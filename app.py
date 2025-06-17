#!/usr/bin/env python3
import os
import sqlite3
import json
import time
import httpx
import click
from tamga import Tamga
from dotenv import load_dotenv
from datetime import datetime, date
import ibm_boto3
from ibm_botocore.client import Config, ClientError

# Import only the functions that exist and are needed
from utils import (
    # Core site collection functions
    get_random_site,
    get_random_indieblog,
    get_hackernews_stories_by_type,
    get_reduced_indieblog_posts,
    # Main enhanced collection function
    collect_unique_sites_enhanced,
    # Database functions for English detection
    update_site_english_status,
    get_sites_needing_english_check,
    # Markdown generation functions
    generate_hackernews_markdown,
    generate_indieblog_markdown,
    save_markdown_report,
    # Analysis functions
    analyze_existing_sites_for_english,
    generate_markdown_from_existing_data,
    check_512kb_site_is_english,
)

# Load environment variables
load_dotenv()

# Configure tamga logger, will set console to false after testing
logger = Tamga(logToJSON=True, logToConsole=True)

# Constants for IBM COS values
COS_ENDPOINT = os.getenv("COS_ENDPOINT")
COS_API_KEY = os.getenv("CLOUD_OBJECT_STORAGE_APIKEY")
COS_INSTANCE_CRN = os.getenv("CLOUD_OBJECT_STORAGE_RESOURCE_INSTANCE_ID")
DB_FILENAME = "random_sites.db"
COS_BUCKET_NAME = os.getenv("COS_BUCKET_NAME")

# Create client
cos_client = ibm_boto3.client(
    "s3",
    ibm_api_key_id=COS_API_KEY,
    ibm_service_instance_id=COS_INSTANCE_CRN,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT,
)


# had to add these functions to handle datetime conversion properly in updated sqlite3
def adapt_datetime(dt):
    return dt.isoformat()


def convert_datetime(s):
    return datetime.fromisoformat(s)


sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("TIMESTAMP", convert_datetime)


def init_database_enhanced():
    """Initialize the SQLite database with enhanced schema for English detection."""
    logger.debug("Initializing enhanced database")
    conn = sqlite3.connect("random_sites.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # Check if the table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sites'")
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        # Create table with full schema including English detection fields
        cursor.execute(
            """
        CREATE TABLE sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            source TEXT,
            capture_date TIMESTAMP,
            has_blog BOOLEAN DEFAULT NULL,
            blog_status TEXT DEFAULT NULL,
            blog_posts_md TEXT DEFAULT NULL,
            last_blog_check TIMESTAMP DEFAULT NULL
        )
        """
        )

        # Create indexes
        cursor.execute(
            """
            CREATE INDEX idx_sites_english_analysis
            ON sites(source, has_blog, last_blog_check)
        """
        )

        logger.info("Created new database with enhanced schema")
    else:
        # Check what columns exist
        cursor.execute("PRAGMA table_info(sites)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        # Add source column if it doesn't exist (legacy support)
        if "source" not in column_names:
            cursor.execute("ALTER TABLE sites ADD COLUMN source TEXT")
            cursor.execute(
                "UPDATE sites SET source = '512kb.club' WHERE source IS NULL"
            )

        # Add English detection columns if they don't exist
        new_columns = [
            ("has_blog", "BOOLEAN DEFAULT NULL"),
            ("blog_status", "TEXT DEFAULT NULL"),
            ("blog_posts_md", "TEXT DEFAULT NULL"),
            ("last_blog_check", "TIMESTAMP DEFAULT NULL"),
        ]

        for column_name, column_def in new_columns:
            if column_name not in column_names:
                cursor.execute(
                    f"ALTER TABLE sites ADD COLUMN {column_name} {column_def}"
                )
                logger.info(f"Added column: {column_name}")

        # Create index if it doesn't exist
        try:
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sites_english_analysis
                ON sites(source, has_blog, last_blog_check)
            """
            )
        except sqlite3.Error as e:
            logger.debug(f"Index may already exist: {e}")

    conn.commit()
    conn.close()
    logger.debug("Enhanced database initialized successfully")


def url_exists(url):
    """Check if a URL already exists in the database."""
    conn = sqlite3.connect("random_sites.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM sites WHERE url = ?", (url,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def add_url_to_db(url, title, source):
    """Add a URL to the database with current timestamp and source."""
    conn = sqlite3.connect("random_sites.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute(
        "INSERT INTO sites (url, title, source, capture_date) VALUES (?, ?, ?, ?)",
        (url, title, source, now),
    )
    conn.commit()
    conn.close()
    logger.info(f"Added to database: {url} - {title} from {source}")


def send_discord_webhook(urls_and_titles):
    """Send a Discord webhook with the collected sites as clickable links.

    Args:
        urls_and_titles: List of (url, title, source) tuples
    """
    logger.info("Sending Discord webhook...")

    # Discord webhook URL - store this in an environment variable in production
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        logger.error("Discord webhook URL not found in environment variables")
        return False

    # Group sites by source
    sites_by_source = {}
    for url, title, source in urls_and_titles:
        if source not in sites_by_source:
            sites_by_source[source] = []

        # Clean up title for formatting
        clean_title = (
            title.replace("[", "\\[")
            .replace("]", "\\]")
            .replace("*", "\\*")
            .replace("_", "\\_")
        )
        if len(clean_title) > 50:
            clean_title = clean_title[:47] + "..."

        sites_by_source[source].append((url, clean_title))

    # Format the message with clickable links
    today = date.today().strftime("%Y-%m-%d")

    # Create embeds for each source
    embeds = []

    for source, sites in sites_by_source.items():
        site_list = "\n".join([f"• [{title}]({url})" for url, title in sites])
        embeds.append(
            {
                "title": f"Sites from {source}",
                "description": site_list,
                "color": 3447003,  # Discord blue color
            }
        )

    # Create webhook payload
    payload = {"content": f"📚 **Random sites collection** - {today}", "embeds": embeds}

    # Send webhook using httpx
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                webhook_url, json=payload, headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
        logger.info("Discord webhook sent successfully")
        return True
    except Exception as e:
        logger.error(f"Error sending Discord webhook: {e}")
        return False


def download_db_from_cos():
    """Download the SQLite database from IBM Cloud Object Storage if it exists."""
    local_file_path = DB_FILENAME

    try:
        # Check if file exists in COS
        try:
            cos_client.head_object(Bucket=COS_BUCKET_NAME, Key=DB_FILENAME)
            file_exists = True
        except ClientError:
            file_exists = False

        if file_exists:
            logger.info(f"Downloading database from COS bucket {COS_BUCKET_NAME}")
            # Download the file
            with open(local_file_path, "wb") as f:
                cos_client.download_fileobj(COS_BUCKET_NAME, DB_FILENAME, f)
            logger.info(f"Database successfully downloaded to {local_file_path}")
        else:
            logger.info(
                "Database file does not exist in COS. A new one will be created locally."
            )
            # Create empty file that will be initialized later
            open(local_file_path, "a").close()

        return True
    except Exception as e:
        logger.error(f"Error downloading database from COS: {e}")
        return False


def upload_db_to_cos():
    """Upload the SQLite database to IBM Cloud Object Storage."""
    local_file_path = DB_FILENAME

    try:
        logger.info(f"Uploading database to COS bucket {COS_BUCKET_NAME}")
        # Upload the file
        with open(local_file_path, "rb") as f:
            cos_client.upload_fileobj(f, COS_BUCKET_NAME, DB_FILENAME)
        logger.info(f"Database successfully uploaded to COS bucket {COS_BUCKET_NAME}")
        return True
    except Exception as e:
        logger.error(f"Error uploading database to COS: {e}")
        return False


def collect_unique_sites(local=False):
    """Main collection function using enhanced site collection with English detection."""
    logger.info("Starting enhanced collection of unique sites with English detection")

    # Download the database from COS first (skip if in local mode)
    if not local:
        if not download_db_from_cos():
            logger.error(
                "Failed to download database from COS. Using/creating local database only."
            )
    else:
        logger.info("Running in local mode, skipping download from COS")

    # Initialize the enhanced database
    init_database_enhanced()

    # Use the enhanced collection function
    collected_sites, markdown_content = collect_unique_sites_enhanced(
        local=local, url_exists_func=url_exists, add_url_to_db_func=add_url_to_db
    )

    # After all operations, upload the updated database back to COS (skip if in local mode)
    if not local:
        upload_db_to_cos()
    else:
        logger.info("Running in local mode, skipping upload to COS")

    # Send collected sites to webhooks if we found any
    if collected_sites:
        discord_result = send_discord_webhook(collected_sites)
        logger.info(f"Webhook results - Discord: {discord_result}")

    # Log markdown generation results
    if markdown_content:
        logger.info(
            f"Generated markdown report with {len(markdown_content)} characters"
        )
    else:
        logger.warning("No markdown content generated")


@click.command()
@click.option(
    "--local", is_flag=True, help="Run in local mode, skipping cloud storage operations"
)
@click.option(
    "--analyze-english",
    is_flag=True,
    help="Analyze existing 512kb sites for English language",
)
@click.option(
    "--generate-markdown",
    is_flag=True,
    help="Generate markdown report from existing data",
)
def main(local, analyze_english, generate_markdown):
    """Collect unique random sites and store them in a database."""
    if analyze_english:
        click.echo("Analyzing existing sites for English language...")
        analyze_existing_sites_for_english()
    elif generate_markdown:
        click.echo("Generating markdown from existing data...")
        generate_markdown_from_existing_data()
    else:
        if local:
            click.echo("Running in local mode (no cloud storage operations)")
        collect_unique_sites(local=local)


if __name__ == "__main__":
    main()

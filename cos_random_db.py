import os
import sqlite3
import json
import time
import httpx
from tamga import Tamga
from datetime import datetime, date
from playwright.sync_api import sync_playwright
import ibm_boto3
from ibm_botocore.client import Config, ClientError

# Configure tamga logger, will set console to false after testing
logger = Tamga(logToJSON=True, logToConsole=True)

# Constants for IBM COS values
COS_ENDPOINT = os.getenv("COS_ENDPOINT")
COS_API_KEY = os.getenv("COS_API_KEY")
COS_INSTANCE_CRN = os.getenv("COS_INSTANCE_CRN")
DB_FILENAME = "random_sites.db"
COS_BUCKET_NAME = os.getenv("COS_BUCKET_NAME") 


# Create client
cos_client = ibm_boto3.client("s3",
    ibm_api_key_id=COS_API_KEY,
    ibm_service_instance_id=COS_INSTANCE_CRN,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT
)

# had to add these functions to handle datetime conversion properly in updated sqlite3
def adapt_datetime(dt):
    return dt.isoformat()


def convert_datetime(s):
    return datetime.fromisoformat(s)


sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("TIMESTAMP", convert_datetime)


def init_database():
    """Initialize the SQLite database if it doesn't exist."""
    logger.debug("Initializing database")
    conn = sqlite3.connect("random_sites.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    
    # Check if the table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sites'")
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        cursor.execute(
            """
        CREATE TABLE sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            source TEXT,
            capture_date TIMESTAMP
        )
        """
        )
    else:
        # Check if source column exists
        cursor.execute("PRAGMA table_info(sites)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Add source column if it doesn't exist
        if "source" not in column_names:
            cursor.execute("ALTER TABLE sites ADD COLUMN source TEXT")
            # Set default source for existing entries
            cursor.execute("UPDATE sites SET source = '512kb.club' WHERE source IS NULL")
    
    conn.commit()
    conn.close()
    logger.debug("Database initialized successfully")


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


def get_random_site():
    """Get a random site from 512kb.club and return its URL and title."""
    logger.debug("Getting random site from 512kb.club")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://512kb.club")

        # Set up event listener for new pages before clicking
        with context.expect_page() as new_page_info:
            # Click the random button
            page.click("a.button.random")

        # Get the new page that was opened
        new_page = new_page_info.value
        new_page.wait_for_load_state("networkidle")

        # Grab the URL and title of the new page
        random_url = new_page.url
        title = new_page.title()

        browser.close()
        logger.debug(f"Retrieved random site: {random_url}")
        return random_url, title


def get_random_indieblog():
    """Get a random site from indieblog.page and return its URL and title."""
    logger.debug("Getting random site from indieblog.page")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://indieblog.page/")

        # Set up event listener for new pages before clicking
        with context.expect_page() as new_page_info:
            # Click the random button using the correct selector from HTML
            page.click("a#stumble")

        # Get the new page that was opened
        new_page = new_page_info.value
        new_page.wait_for_load_state("networkidle")

        # Grab the URL and title of the new page
        random_url = new_page.url
        title = new_page.title()

        browser.close()
        logger.debug(f"Retrieved random site: {random_url}")
        return random_url, title

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
        clean_title = title.replace("[", "\\[").replace("]", "\\]").replace("*", "\\*").replace("_", "\\_")
        if len(clean_title) > 50:
            clean_title = clean_title[:47] + "..."
            
        sites_by_source[source].append((url, clean_title))

    # Format the message with clickable links
    today = date.today().strftime("%Y-%m-%d")
    
    # Create embeds for each source
    embeds = []
    
    for source, sites in sites_by_source.items():
        site_list = "\n".join([f"• [{title}]({url})" for url, title in sites])
        embeds.append({
            "title": f"Sites from {source}",
            "description": site_list,
            "color": 3447003,  # Discord blue color
        })

    # Create webhook payload
    payload = {
        "content": f"📚 **Random sites collection** - {today}",
        "embeds": embeds
    }

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
            with open(local_file_path, 'wb') as f:
                cos_client.download_fileobj(COS_BUCKET_NAME, DB_FILENAME, f)
            logger.info(f"Database successfully downloaded to {local_file_path}")
        else:
            logger.info("Database file does not exist in COS. A new one will be created locally.")
            # Create empty file that will be initialized later
            open(local_file_path, 'a').close()
            
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
        with open(local_file_path, 'rb') as f:
            cos_client.upload_fileobj(f, COS_BUCKET_NAME, DB_FILENAME)
        logger.info(f"Database successfully uploaded to COS bucket {COS_BUCKET_NAME}")
        return True
    except Exception as e:
        logger.error(f"Error uploading database to COS: {e}")
        return False

def collect_ten_unique_sites():
    """Collect 5 unique random sites from each source, store in DB and send to webhooks."""
    logger.info("Starting collection of unique sites")
    
    # Download the database from COS first
    if not download_db_from_cos():
        logger.error("Failed to download database from COS. Using/creating local database only.")
    
    # Initialize the database (now local)
    init_database()
    
    sources = ["512kb.club", "indieblog.page"]
    collected_sites = []  # Store the collected sites
    
    for source in sources:
        unique_sites_collected = 0
        attempts = 0
        max_attempts = 15  # Allow more attempts to find unique sites
        
        logger.info(f"Collecting 5 sites from {source}")
        while unique_sites_collected < 5 and attempts < max_attempts:
            logger.info(f"Finding site {unique_sites_collected + 1}/5 from {source}...")
            try:
                if source == "512kb.club":
                    url, title = get_random_site()
                else:  # indieblog.page
                    url, title = get_random_indieblog()
                    
                if not url_exists(url):
                    add_url_to_db(url, title, source)
                    collected_sites.append((url, title, source))  # Include source
                    unique_sites_collected += 1
                else:
                    logger.info(f"Site already in database: {url}")

                time.sleep(2)
            except Exception as e:
                logger.error(f"Error getting random site from {source}: {e}")

            attempts += 1

        logger.info(
            f"Collection from {source} complete. Added {unique_sites_collected} new sites to database."
        )

    # After all operations, upload the updated database back to COS
    upload_db_to_cos()
    
    # Send collected sites to webhooks if we found any
    if collected_sites:
        discord_result = send_discord_webhook(collected_sites)
        logger.info(f"Webhook results - Discord: {discord_result}")


if __name__ == "__main__":
    collect_ten_unique_sites()

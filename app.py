#!/usr/bin/env python3
# Author: Ryan Tiffany
# Copyright (c) 2025 Ryan Tiffany
import os
import json
import time
import httpx
import psycopg2
import psycopg2.extras
import base64
import tempfile
from tamga import Tamga
from datetime import datetime, date
from playwright.sync_api import sync_playwright

# Configure tamga logger, will set console to false after testing
logger = Tamga(logToJSON=True, logToConsole=True)

# Remove SQLite-specific code since we're moving to PostgreSQL

def get_connection_details():
    """Extract PostgreSQL connection details from environment variable."""
    connection_json = os.environ.get("PSQL_CONNECTION")
    if not connection_json:
        logger.error("PSQL_CONNECTION environment variable not set")
        raise ValueError("PSQL_CONNECTION environment variable not set")
    
    try:
        connection_info = json.loads(connection_json)
        
        # Extract connection parameters from the postgres section
        postgres_info = connection_info.get("postgres", {})
        uri_info = postgres_info.get("hosts", [{}])[0]
        auth_info = postgres_info.get("authentication", {})
        
        # Build connection parameters
        db_params = {
            "dbname": postgres_info.get("database", ""),
            "user": auth_info.get("username", ""),
            "password": auth_info.get("password", ""),
            "host": uri_info.get("hostname", ""),
            "port": uri_info.get("port", 5432),
            "sslmode": postgres_info.get("query_options", {}).get("sslmode", "verify-full")
        }
        
        # Get SSL certificate
        cert_base64 = postgres_info.get("certificate", {}).get("certificate_base64", "")
        
        return db_params, cert_base64
    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Error parsing PSQL_CONNECTION: {str(e)}")
        raise ValueError(f"Invalid PSQL_CONNECTION format: {str(e)}")

def setup_ssl_cert(cert_base64):
    """Setup SSL certificate for PostgreSQL connection."""
    if not cert_base64:
        logger.error("SSL certificate not found in connection details")
        raise ValueError("SSL certificate not found in connection details")
        
    cert_file = tempfile.NamedTemporaryFile(delete=False, suffix=".crt")
    cert_file.write(base64.b64decode(cert_base64))
    cert_file.close()
    
    # Store the path for future use
    os.environ["PG_CERT_PATH"] = cert_file.name
    logger.debug(f"SSL certificate saved to {cert_file.name}")
    return cert_file.name

def get_db_connection():
    """Get a connection to PostgreSQL database using environment variables."""
    # Get certificate path from environment or create new one
    cert_path = os.environ.get("PG_CERT_PATH")
    
    try:
        db_params, cert_base64 = get_connection_details()
        
        if not cert_path and cert_base64:
            cert_path = setup_ssl_cert(cert_base64)
            
        # Add SSL certificate path to connection parameters
        if cert_path:
            db_params["sslrootcert"] = cert_path
            
        # Connect to database
        conn = psycopg2.connect(**db_params)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

def init_database():
    """Initialize the PostgreSQL database if tables don't exist."""
    logger.debug("Initializing database")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if the table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'sites'
        )
    """)
    table_exists = cursor.fetchone()[0]
    
    if not table_exists:
        cursor.execute("""
            CREATE TABLE sites (
                id SERIAL PRIMARY KEY,
                url TEXT UNIQUE,
                title TEXT,
                source TEXT,
                capture_date TIMESTAMP
            )
        """)
        logger.debug("Created sites table")
    else:
        # Check if source column exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'sites' 
                AND column_name = 'source'
            )
        """)
        source_column_exists = cursor.fetchone()[0]
        
        # Add source column if it doesn't exist
        if not source_column_exists:
            cursor.execute("ALTER TABLE sites ADD COLUMN source TEXT")
            # Set default source for existing entries
            cursor.execute("UPDATE sites SET source = '512kb.club' WHERE source IS NULL")
            logger.debug("Added source column to sites table")
    
    conn.commit()
    cursor.close()
    conn.close()
    logger.debug("Database initialized successfully")

def url_exists(url):
    """Check if a URL already exists in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM sites WHERE url = %s", (url,))  # Using %s for PostgreSQL
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists

def add_url_to_db(url, title, source):
    """Add a URL to the database with current timestamp and source."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute(
        "INSERT INTO sites (url, title, source, capture_date) VALUES (%s, %s, %s, %s)",
        (url, title, source, now)
    )
    conn.commit()
    cursor.close()
    conn.close()
    logger.info(f"Added to database: {url} - {title} from {source}")

def test_db_connection():
    """Test if the database connection is working."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        logger.info(f"Database connection successful. PostgreSQL version: {version[0]}")
        return True
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return False

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

def collect_ten_unique_sites():
    """Collect 5 unique random sites from each source that aren't in the database yet and send to webhooks."""
    logger.info("Starting collection of unique sites")
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
                    collected_sites.append((url, title, source))  
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

    # Send collected sites to webhooks if we found any
    if collected_sites:
        discord_result = send_discord_webhook(collected_sites)
        
        logger.info(f"Webhook results - Discord: {discord_result}")


if __name__ == "__main__":
    collect_ten_unique_sites()

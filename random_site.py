import os
import sqlite3
import json
import time
import httpx
from tamga import Tamga
from datetime import datetime, date
from playwright.sync_api import sync_playwright

# Configure tamga logger, will set console to false after testing
logger = Tamga(logToJSON=True, logToConsole=True)


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
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        title TEXT,
        capture_date TIMESTAMP
    )
    """
    )
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


def add_url_to_db(url, title):
    """Add a URL to the database with current timestamp."""
    conn = sqlite3.connect("random_sites.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute(
        "INSERT INTO sites (url, title, capture_date) VALUES (?, ?, ?)",
        (url, title, now),
    )
    conn.commit()
    conn.close()
    logger.info(f"Added to database: {url} - {title}")


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


def send_discord_webhook(urls_and_titles):
    """Send a Discord webhook with the collected sites in a table format.

    Args:
        urls_and_titles: List of (url, title) tuples
    """
    logger.info("Sending Discord webhook...")

    # Discord webhook URL - store this in an environment variable in production
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        logger.error("Discord webhook URL not found in environment variables")
        return False

    # Format data as table
    today = date.today().strftime("%Y-%m-%d")
    table_rows = []
    for url, title in urls_and_titles:
        # Clean up title for markdown formatting
        clean_title = title.replace("|", "\\|").replace("*", "\\*").replace("_", "\\_")
        if len(clean_title) > 40:
            clean_title = clean_title[:37] + "..."
        table_rows.append(f"{clean_title} | {url}")

    table_header = "Site Name | URL\n---------|----------\n"
    table_content = table_header + "\n".join(table_rows)

    # Create webhook payload
    payload = {
        "content": f"📚 **Random sites from 512kb.club** - {today}",
        "embeds": [
            {
                "title": "Discovered Sites",
                "description": f"```\n{table_content}\n```",
                "color": 3447003,  # Discord blue color
            }
        ],
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


def collect_five_unique_sites():
    """Collect 5 unique random sites that aren't in the database yet and send to Discord."""
    logger.info("Starting collection of unique sites")
    init_database()
    unique_sites_collected = 0
    attempts = 0
    collected_sites = []  # Store the collected sites
    max_attempts = 10

    while unique_sites_collected < 10 and attempts < max_attempts:
        logger.info(f"Finding site {unique_sites_collected + 1}/10...")
        try:
            url, title = get_random_site()
            if not url_exists(url):
                add_url_to_db(url, title)
                collected_sites.append((url, title))  # Add to our collection
                unique_sites_collected += 1
            else:
                logger.info(f"Site already in database: {url}")

            time.sleep(2)
        except Exception as e:
            logger.error(f"Error getting random site: {e}")

        attempts += 1

    logger.info(
        f"Collection complete. Added {unique_sites_collected} new sites to database."
    )

    # Send collected sites to Discord if we found any
    if collected_sites:
        send_discord_webhook(collected_sites)


if __name__ == "__main__":
    collect_five_unique_sites()

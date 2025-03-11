import os
import sqlite3
import time
from tamga import Tamga
from datetime import datetime
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


def collect_five_unique_sites():
    """Collect 5 unique random sites that aren't in the database yet."""
    logger.info("Starting collection of unique sites")
    init_database()
    unique_sites_collected = 0
    attempts = 0
    # Had to set a limit the number of attempts to avoid infinite loop when the network is flaky
    max_attempts = 10

    while unique_sites_collected < 10 and attempts < max_attempts:
        logger.info(f"Finding site {unique_sites_collected + 1}/10...")
        try:
            url, title = get_random_site()
            if not url_exists(url):
                add_url_to_db(url, title)
                unique_sites_collected += 1
            else:
                logger.info(f"Site already in database: {url}")

            # Add small delay between requests to be nice to the server aka empathy for the machine
            time.sleep(2)
        except Exception as e:
            logger.error(f"Error getting random site: {e}")

        attempts += 1

    logger.info(
        f"Collection complete. Added {unique_sites_collected} new sites to database."
    )


if __name__ == "__main__":
    collect_five_unique_sites()

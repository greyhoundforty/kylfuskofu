#!/usr/bin/env python3
import os
import sqlite3
import time
from datetime import datetime, date
from tamga import Tamga
import ibm_boto3
from ibm_botocore.client import Config
import rfeed

# Configure tamga logger
logger = Tamga(logToJSON=True, logToConsole=True)

# Constants for IBM COS
COS_ENDPOINT = os.getenv("COS_ENDPOINT")
COS_API_KEY = os.getenv("CLOUD_OBJECT_STORAGE_APIKEY")
COS_INSTANCE_CRN = os.getenv("CLOUD_OBJECT_STORAGE_RESOURCE_INSTANCE_ID")
DB_FILENAME = "random_sites.db"
RSS_FILENAME = "random_sites.xml"
COS_BUCKET_NAME = os.getenv("COS_BUCKET_NAME")
COS_STATIC_BUCKET_NAME = os.getenv("COS_STATIC_BUCKET_NAME")

# Create COS client
cos_client = ibm_boto3.client(
    "s3",
    ibm_api_key_id=COS_API_KEY,
    ibm_service_instance_id=COS_INSTANCE_CRN,
    config=Config(signature_version="oauth"),
    endpoint_url=COS_ENDPOINT,
)


# Register SQLite adapters/converters
def adapt_datetime(dt):
    return dt.isoformat()


def convert_datetime(s):
    return datetime.fromisoformat(s)


sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("TIMESTAMP", convert_datetime)


def download_db_from_cos():
    """Download the SQLite database from IBM Cloud Object Storage."""
    try:
        logger.info(f"Downloading database from COS bucket {COS_BUCKET_NAME}")
        with open(DB_FILENAME, "wb") as f:
            cos_client.download_fileobj(COS_BUCKET_NAME, DB_FILENAME, f)
        logger.info(f"Database successfully downloaded to {DB_FILENAME}")
        return True
    except Exception as e:
        logger.error(f"Error downloading database from COS: {e}")
        return False


def upload_rss_to_cos(rss_content):
    """Upload the RSS feed to IBM Cloud Object Storage."""
    try:
        logger.info(f"Uploading RSS feed to COS bucket {COS_STATIC_BUCKET_NAME}")
        cos_client.put_object(
            Bucket=COS_STATIC_BUCKET_NAME,
            Key=RSS_FILENAME,
            Body=rss_content,
            ContentType="application/rss+xml",
        )
        logger.info(f"RSS feed successfully uploaded to COS")

        # Make the RSS feed publicly accessible
        cos_client.put_object_acl(
            Bucket=COS_STATIC_BUCKET_NAME, Key=RSS_FILENAME, ACL="public-read"
        )
        logger.info("RSS feed set to public-read")

        return True
    except Exception as e:
        logger.error(f"Error uploading RSS feed to COS: {e}")
        return False


def get_sites_from_db():
    """Get all sites from the SQLite database."""
    conn = sqlite3.connect(DB_FILENAME, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # Get all sites, ordered by capture date (newest first)
    cursor.execute(
        "SELECT url, title, source, capture_date FROM sites ORDER BY capture_date DESC"
    )
    sites = cursor.fetchall()

    conn.close()
    return sites


def generate_rss_feed(sites):
    """Generate an RSS feed from the site data."""
    items = []

    for url, title, source, capture_date in sites:
        # Create an RSS item for each site
        item = rfeed.Item(
            title=title,
            link=url,
            description=f"Discovered from {source} on {capture_date.strftime('%Y-%m-%d')}",
            guid=rfeed.Guid(url),
            pubDate=capture_date,
        )
        items.append(item)

    # Create the feed
    feed = rfeed.Feed(
        title="Random Web Discovery Feed",
        link="https://github.com/greyhoundforty/kylfuskofu",
        description="A collection of randomly discovered websites from 512kb.club and indieblog.page",
        language="en-US",
        lastBuildDate=datetime.now(),
        items=items,
    )

    return feed.rss()


def process_db_to_rss():
    """Main function to process the DB and generate RSS."""
    logger.info("Starting RSS feed generation")

    # Download the database
    if not download_db_from_cos():
        logger.error("Failed to download database, aborting RSS generation")
        return False

    # Get sites from database
    sites = get_sites_from_db()
    logger.info(f"Retrieved {len(sites)} sites from database")

    # Generate RSS feed
    rss_content = generate_rss_feed(sites)
    logger.info("RSS feed generated successfully")

    # Upload to COS
    if upload_rss_to_cos(rss_content):
        rss_url = f"{COS_ENDPOINT}/{COS_STATIC_BUCKET_NAME}/{RSS_FILENAME}"
        logger.info(f"RSS feed available at: {rss_url}")
        return True

    return False


if __name__ == "__main__":
    process_db_to_rss()

from flask import current_app, g
import sqlite3
import os
import traceback
from .logger import logger

DATABASE = "instance/catalog.db"


def get_db():
    if "db" not in g:
        try:
            # Ensure the database path exists
            os.makedirs(os.path.dirname(current_app.config["DATABASE"]), exist_ok=True)

            # Connect WITHOUT automatic type detection for timestamps
            g.db = sqlite3.connect(
                current_app.config["DATABASE"]
                # Removed detect_types=sqlite3.PARSE_DECLTYPES to avoid timestamp conversion
            )
            g.db.row_factory = sqlite3.Row
            logger.debug(f"Connected to database: {current_app.config['DATABASE']}")
        except Exception as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)


def get_random_entries(count):
    logger.info(f"Fetching {count} random entries from sites table")
    db = get_db()
    try:
        # First, check if the table exists
        logger.debug("Checking if sites table exists")
        table_check_query = (
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sites'"
        )
        table_check_result = db.execute(table_check_query).fetchone()

        if not table_check_result:
            logger.error("Sites table does not exist")
            return []

        logger.debug("Sites table exists, querying for random entries")

        # Query the sites table for random entries
        cursor = db.execute(
            "SELECT id, url, title, source, capture_date FROM sites ORDER BY RANDOM() LIMIT ?",
            (count,),
        )

        entries = []
        for row in cursor:
            # Manually create a dictionary without relying on automatic conversions
            entry = {
                "id": row["id"],
                "url": row["url"],
                "title": row["title"],
                "source": row["source"],
                "capture_date": row["capture_date"],  # Store as-is without conversion
            }
            entries.append(entry)

        logger.info(f"Retrieved {len(entries)} entries from sites table")
        return entries
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        # Print full stack trace for debugging
        logger.error(traceback.format_exc())
        return []


def get_entries_by_source(source, limit=10):
    logger.info(f"Fetching {limit} entries from source: {source}")
    db = get_db()
    try:
        cursor = db.execute(
            "SELECT id, url, title, source, capture_date FROM sites WHERE source = ? ORDER BY RANDOM() LIMIT ?",
            (source, limit),
        )

        entries = []
        for row in cursor:
            entry = {
                "id": row["id"],
                "url": row["url"],
                "title": row["title"],
                "source": row["source"],
                "capture_date": row["capture_date"],
            }
            entries.append(entry)

        logger.info(f"Retrieved {len(entries)} entries from source: {source}")
        return entries
    except Exception as e:
        logger.error(f"Database error fetching entries by source: {str(e)}")
        return []

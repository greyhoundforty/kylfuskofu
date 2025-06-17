#!/usr/bin/env python3
"""
Database migration script and integration guide for enhanced scrapers
"""

import sqlite3
import os
from datetime import datetime
from tamga import Tamga

logger = Tamga(logToJSON=True, logToConsole=True)


def migrate_database_schema():
    """
    Migrate the existing database to support blog analysis features.
    This should be run once before deploying the enhanced scraper.
    """
    db_path = "random_sites.db"

    if not os.path.exists(db_path):
        logger.error(f"Database {db_path} not found. Please run the main app first.")
        return False

    try:
        # Create backup
        backup_path = (
            f"random_sites_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        import shutil

        shutil.copy2(db_path, backup_path)
        logger.info(f"Created database backup: {backup_path}")

        conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()

        # Check current schema
        cursor.execute("PRAGMA table_info(sites)")
        columns = [col[1] for col in cursor.fetchall()]

        # Add new columns if they don't exist
        new_columns = [
            ("has_blog", "BOOLEAN DEFAULT NULL"),
            ("blog_status", "TEXT DEFAULT NULL"),
            ("blog_posts_md", "TEXT DEFAULT NULL"),
            ("last_blog_check", "TIMESTAMP DEFAULT NULL"),
        ]

        for column_name, column_def in new_columns:
            if column_name not in columns:
                sql = f"ALTER TABLE sites ADD COLUMN {column_name} {column_def}"
                cursor.execute(sql)
                logger.info(f"Added column: {column_name}")
            else:
                logger.info(f"Column {column_name} already exists")

        # Create index for blog analysis queries
        try:
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sites_blog_analysis
                ON sites(source, has_blog, last_blog_check)
            """
            )
            logger.info("Created blog analysis index")
        except sqlite3.Error as e:
            logger.warning(f"Could not create index: {e}")

        conn.commit()
        conn.close()

        logger.info("Database migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        return False


def verify_migration():
    """Verify that the migration was successful."""
    try:
        conn = sqlite3.connect("random_sites.db", detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()

        # Check schema
        cursor.execute("PRAGMA table_info(sites)")
        columns = [col[1] for col in cursor.fetchall()]

        expected_columns = [
            "id",
            "url",
            "title",
            "source",
            "capture_date",
            "has_blog",
            "blog_status",
            "blog_posts_md",
            "last_blog_check",
        ]

        missing_columns = [col for col in expected_columns if col not in columns]

        if missing_columns:
            logger.error(f"Migration incomplete. Missing columns: {missing_columns}")
            return False

        # Test insert/update operations
        cursor.execute(
            """
            SELECT COUNT(*) FROM sites
            WHERE source = '512kb.club'
            LIMIT 1
        """
        )

        logger.info("Migration verification passed")
        conn.close()
        return True

    except Exception as e:
        logger.error(f"Migration verification failed: {e}")
        return False


# Modified init_database function for app.py
def init_database_enhanced():
    """Enhanced version of init_database with new schema."""
    logger.debug("Initializing enhanced database")
    conn = sqlite3.connect("random_sites.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # Check if the table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sites'")
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        # Create table with full schema
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
            CREATE INDEX idx_sites_blog_analysis
            ON sites(source, has_blog, last_blog_check)
        """
        )

        logger.info("Created new database with enhanced schema")
    else:
        # Check if source column exists (existing migration logic)
        cursor.execute("PRAGMA table_info(sites)")
        columns = [col[1] for col in cursor.fetchall()]

        # Add source column if it doesn't exist (existing logic)
        if "source" not in columns:
            cursor.execute("ALTER TABLE sites ADD COLUMN source TEXT")
            cursor.execute(
                "UPDATE sites SET source = '512kb.club' WHERE source IS NULL"
            )

        # Add new blog-related columns if they don't exist
        new_columns = [
            ("has_blog", "BOOLEAN DEFAULT NULL"),
            ("blog_status", "TEXT DEFAULT NULL"),
            ("blog_posts_md", "TEXT DEFAULT NULL"),
            ("last_blog_check", "TIMESTAMP DEFAULT NULL"),
        ]

        for column_name, column_def in new_columns:
            if column_name not in columns:
                cursor.execute(
                    f"ALTER TABLE sites ADD COLUMN {column_name} {column_def}"
                )
                logger.info(f"Added column: {column_name}")

    conn.commit()
    conn.close()
    logger.debug("Enhanced database initialized successfully")


# Integration modifications for app.py
"""
INTEGRATION GUIDE FOR app.py:

1. Replace the init_database() function call with init_database_enhanced()

2. Replace the collect_unique_sites() function with collect_unique_sites_enhanced()

3. Update the imports section:

from utils import (
    get_random_site,
    get_random_indieblog,
    get_random_hackernews_stories,
    get_random_linkwarden_links,
    # Add new imports:
    analyze_512kb_site_for_blog,
    update_site_blog_status,
    get_hackernews_stories_by_type,
    generate_hackernews_markdown,
    get_reduced_indieblog_posts,
    generate_indieblog_markdown,
    save_markdown_report
)

4. Add new CLI options for blog analysis:

@click.option('--analyze-blogs', is_flag=True, help='Analyze existing 512kb sites for blogs')
@click.option('--generate-markdown', is_flag=True, help='Generate markdown report only')
def main(local, analyze_blogs, generate_markdown):
    if analyze_blogs:
        analyze_existing_sites_for_blogs()
    elif generate_markdown:
        generate_markdown_from_existing_data()
    else:
        collect_unique_sites_enhanced(local=local)

5. Optional: Add these new functions to app.py:
"""


def analyze_existing_sites_for_blogs(limit=50):
    """Analyze existing 512kb sites that haven't been checked for blogs."""
    logger.info("Analyzing existing 512kb sites for blog content")

    conn = sqlite3.connect("random_sites.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # Get sites that need analysis
    cursor.execute(
        """
        SELECT url, title FROM sites
        WHERE source = '512kb.club'
        AND (has_blog IS NULL OR last_blog_check IS NULL)
        LIMIT ?
    """,
        (limit,),
    )

    sites_to_analyze = cursor.fetchall()
    conn.close()

    logger.info(f"Found {len(sites_to_analyze)} sites to analyze")

    for i, (url, title) in enumerate(sites_to_analyze, 1):
        logger.info(f"Analyzing {i}/{len(sites_to_analyze)}: {url}")

        try:
            has_blog, posts_md, status = analyze_512kb_site_for_blog(url, title)
            update_site_blog_status(url, has_blog, status, posts_md)

            # Rate limiting
            time.sleep(3)

        except Exception as e:
            logger.error(f"Failed to analyze {url}: {e}")
            update_site_blog_status(url, False, "error")
            continue

    logger.info("Blog analysis complete")


def generate_markdown_from_existing_data():
    """Generate markdown report from existing analyzed data."""
    logger.info("Generating markdown from existing data")

    conn = sqlite3.connect("random_sites.db", detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    # Get sites with blogs
    cursor.execute(
        """
        SELECT title, blog_posts_md FROM sites
        WHERE has_blog = TRUE
        AND blog_posts_md IS NOT NULL
        AND source = '512kb.club'
        ORDER BY last_blog_check DESC
        LIMIT 20
    """
    )

    blog_sites = cursor.fetchall()

    # Get recent HN stories
    cursor.execute(
        """
        SELECT url, title FROM sites
        WHERE source LIKE 'hackernews-%'
        ORDER BY capture_date DESC
        LIMIT 20
    """
    )

    hn_stories = cursor.fetchall()

    # Get recent indie blogs
    cursor.execute(
        """
        SELECT url, title FROM sites
        WHERE source = 'indieblog.page'
        ORDER BY capture_date DESC
        LIMIT 10
    """
    )

    indie_blogs = cursor.fetchall()
    conn.close()

    # Generate markdown
    markdown_sections = []

    if blog_sites:
        markdown_sections.append("# 512KB Club Sites with Blogs\n")
        for title, posts_md in blog_sites:
            if posts_md:
                markdown_sections.append(posts_md)

    if hn_stories:
        markdown_sections.append("\n# Recent Hacker News Stories\n")
        for url, title in hn_stories:
            markdown_sections.append(f"- [{title}]({url})")

    if indie_blogs:
        markdown_sections.append("\n# Recent IndieWeb Blogs\n")
        for url, title in indie_blogs:
            markdown_sections.append(f"- [{title}]({url})")

    final_markdown = "\n".join(markdown_sections)
    save_markdown_report(final_markdown)


# Configuration options (add to app.py or separate config file)
class ScraperConfig:
    """Configuration for enhanced scrapers."""

    # 512kb scraper settings
    BLOG_ANALYSIS_ENABLED = True
    MAX_BLOG_LINKS_TO_CHECK = 3
    MAX_POSTS_PER_SITE = 5
    BLOG_ANALYSIS_TIMEOUT = 15  # seconds

    # Hacker News settings
    HN_SHOW_STORIES_COUNT = 5
    HN_NEW_STORIES_COUNT = 5
    HN_RATE_LIMIT_DELAY = 0.2  # seconds between API calls

    # IndieWeb settings
    INDIE_POSTS_COUNT = 5
    INDIE_RATE_LIMIT_DELAY = 1  # seconds between requests

    # General settings
    MARKDOWN_OUTPUT_ENABLED = True
    MARKDOWN_SAVE_TO_FILE = True
    PLAYWRIGHT_HEADLESS = True
    REQUEST_TIMEOUT = 10  # seconds


if __name__ == "__main__":
    """
    Run this script to migrate existing database:
    python database_migration.py
    """
    print("Starting database migration...")

    if migrate_database_schema():
        if verify_migration():
            print("✅ Database migration completed successfully")
        else:
            print("❌ Migration verification failed")
    else:
        print("❌ Database migration failed")

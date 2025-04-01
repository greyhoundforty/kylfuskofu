import os
import sqlite3
from datetime import datetime


def add_sample_data():
    # Connect to the database
    db_path = os.path.join("instance", "catalog.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    db = conn

    # Make sure the table exists
    db.execute(
        """
    CREATE TABLE IF NOT EXISTS sites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        title TEXT,
        source TEXT,
        capture_date TIMESTAMP
    )
    """
    )

    # Sample data
    sample_data = [
        ("https://example.com", "Example Website", "Sample", "2025-04-01"),
        (
            "https://www.carbondesignsystem.com",
            "Carbon Design System",
            "IBM",
            "2025-04-01",
        ),
        ("https://www.ibm.com", "IBM", "Corporate", "2025-04-01"),
        (
            "https://sustainable-web.org",
            "Sustainable Web Design",
            "Research",
            "2025-03-15",
        ),
        ("https://www.mozilla.org", "Mozilla", "Open Source", "2025-03-20"),
        ("https://github.com", "GitHub", "Developer", "2025-03-25"),
        ("https://www.figma.com", "Figma", "Design", "2025-03-30"),
        ("https://www.sketch.com", "Sketch", "Design", "2025-04-01"),
        ("https://www.adobe.com", "Adobe", "Design", "2025-04-02"),
        ("https://www.notion.so", "Notion", "Productivity", "2025-04-03"),
    ]

    # Insert data, handling duplicate URLs
    for item in sample_data:
        try:
            db.execute(
                "INSERT INTO sites (url, title, source, capture_date) VALUES (?, ?, ?, ?)",
                item,
            )
            print(f"Added: {item[1]}")
        except sqlite3.IntegrityError:
            print(f"Skipped (already exists): {item[1]}")

    db.commit()

    # Verify data was added
    count = db.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
    print(f"Total records in database: {count}")

    conn.close()


if __name__ == "__main__":
    add_sample_data()

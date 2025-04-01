import sqlite3
import os


def inspect_database():
    db_path = "instance/catalog.db"

    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    db = conn

    # Check tables
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print("Tables in database:")
    for table in tables:
        print(f"- {table['name']}")

    # Check sites table structure
    if any(t["name"] == "sites" for t in tables):
        print("\nSites table structure:")
        columns = db.execute("PRAGMA table_info(sites)").fetchall()
        for col in columns:
            print(f"- {col['name']} ({col['type']})")

        # Check row count
        count = db.execute("SELECT COUNT(*) FROM sites").fetchone()[0]
        print(f"\nRow count in sites table: {count}")

        if count > 0:
            # Display sample row
            sample = db.execute("SELECT * FROM sites LIMIT 1").fetchone()
            print("\nSample row:")
            for key in sample.keys():
                print(f"- {key}: {sample[key]}")

    conn.close()


if __name__ == "__main__":
    inspect_database()

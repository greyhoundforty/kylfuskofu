def get_random_entries(db_connection, table_name, limit=10):
    import random
    import sqlite3

    cursor = db_connection.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    entries = cursor.fetchall()

    if len(entries) > limit:
        return random.sample(entries, limit)
    return entries


def format_entry(entry):
    # Assuming entry is a tuple, convert it to a dictionary or any other format as needed
    return {
        "id": entry[0],
        "title": entry[1],
        "description": entry[2],
        # Add more fields as necessary based on your database schema
    }

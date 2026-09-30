import sqlite3
import os

DB_PATH = 'talentsync.db'
SCHEMA_PATH = 'app/database/schema.sql'

def migrate():
    print(f"Connecting to {DB_PATH}...")
    if not os.path.exists(DB_PATH):
        print("Database not found. Let the app create it natively.")
        return

    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()

    print("Executing schema to ensure new tables exist (IF NOT EXISTS will prevent overwriting)...")
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(schema_sql)
        print("Migration complete. New tables added successfully.")

if __name__ == '__main__':
    migrate()

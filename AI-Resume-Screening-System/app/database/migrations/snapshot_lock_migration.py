"""
Database Migration: Add resume_id column to applications table and backfill existing rows.
Step 3 of Candidate Anti-Gaming Architecture: Snapshot Lock.
"""
import os
import sys
import sqlite3
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))
from app.config.settings import ActiveConfig

def run_migration(db_path: Optional[str] = None):
    if not db_path:
        db_path = getattr(ActiveConfig, 'SQLITE_DB_PATH', 'talentsync.db')
        
    print(f"Applying snapshot lock migration to {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Check existing columns in applications
    columns = [col[1] for col in cur.execute("PRAGMA table_info(applications)").fetchall()]

    if 'resume_id' not in columns:
        cur.execute("ALTER TABLE applications ADD COLUMN resume_id INTEGER REFERENCES resumes(id)")
        print("Added column: resume_id to applications table")

    # 2. Backfill existing applications with user's most recent resume at application time
    cur.execute("""
        UPDATE applications
        SET resume_id = (
            SELECT id FROM resumes
            WHERE resumes.user_id = applications.user_id
            ORDER BY id DESC
            LIMIT 1
        )
        WHERE resume_id IS NULL
    """)
    backfilled_count = cur.rowcount
    print(f"Backfilled {backfilled_count} applications with snapshot resume_id")

    # 3. Create index on resume_id
    cur.execute("CREATE INDEX IF NOT EXISTS idx_applications_resume ON applications(resume_id)")

    conn.commit()
    conn.close()
    print("Snapshot lock migration completed successfully.")

if __name__ == '__main__':
    run_migration()

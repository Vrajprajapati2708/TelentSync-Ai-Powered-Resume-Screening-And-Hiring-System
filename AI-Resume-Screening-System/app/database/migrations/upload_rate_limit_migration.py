"""
Database Migration: Add resume_upload_logs table and backfill from existing resumes.
Step 4 of Candidate Anti-Gaming Architecture: Re-Upload Rate Limiting & Velocity Decoupling.
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
        
    print(f"Applying upload rate limit migration to {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Create resume_upload_logs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resume_upload_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            file_hash   TEXT    DEFAULT '',
            uploaded_at TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_resume_upload_logs_user_time ON resume_upload_logs(user_id, uploaded_at)")
    print("Created resume_upload_logs table and index.")

    # 2. Backfill from existing resumes if resume_upload_logs is empty
    log_count = cur.execute("SELECT COUNT(*) FROM resume_upload_logs").fetchone()[0]
    if log_count == 0:
        cur.execute("""
            INSERT INTO resume_upload_logs (user_id, file_hash, uploaded_at)
            SELECT user_id, file_hash, uploaded_at FROM resumes
        """)
        backfilled = cur.rowcount
        print(f"Backfilled {backfilled} historical uploads into resume_upload_logs.")
    else:
        print(f"resume_upload_logs already contains {log_count} records.")

    conn.commit()
    conn.close()
    print("Upload rate limit migration completed successfully.")

if __name__ == '__main__':
    run_migration()

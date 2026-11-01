"""
TalentSync Migration: Learning Timeline Engine & Velocity Anomaly Detection (Step 7)
Creates `skill_velocity_anomalies` table and indexes for tracking impossible learning velocities
and sudden skill acquisition anomalies across consecutive resume versions.
"""

import os
import sys
import sqlite3

# Ensure app package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))


def run_migration(db_path: str):
    if not os.path.exists(db_path):
        print(f"[!] Database path does not exist: {db_path}")
        return

    print(f"[*] Running Learning Timeline Migration on: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Create skill_velocity_anomalies table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS skill_velocity_anomalies (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id            INTEGER NOT NULL,
            previous_resume_id INTEGER,
            current_resume_id  INTEGER NOT NULL,
            elapsed_days       REAL NOT NULL,
            estimated_days     REAL NOT NULL,
            new_skills         TEXT NOT NULL,
            severity           TEXT NOT NULL DEFAULT 'high',
            velocity_ratio     REAL NOT NULL,
            anomaly_reason     TEXT NOT NULL,
            status             TEXT NOT NULL DEFAULT 'flagged',
            detected_at        TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(previous_resume_id) REFERENCES resumes(id) ON DELETE SET NULL,
            FOREIGN KEY(current_resume_id) REFERENCES resumes(id) ON DELETE CASCADE
        )
    """)

    # 2. Create indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_velocity_anomalies_user ON skill_velocity_anomalies(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_velocity_anomalies_status ON skill_velocity_anomalies(status)")

    conn.commit()
    conn.close()
    print(f"[+] Migration complete for {db_path}.")


if __name__ == '__main__':
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    db_file = os.path.join(base_dir, 'instance', 'talentsync.db')
    if not os.path.exists(db_file):
        db_file = os.path.join(base_dir, 'talentsync.db')

    run_migration(db_file)

    backup_db = os.path.join(base_dir, 'talentsync_backup_phase5.db')
    if os.path.exists(backup_db):
        run_migration(backup_db)

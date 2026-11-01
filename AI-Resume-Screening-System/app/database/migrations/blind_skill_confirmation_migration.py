"""
TalentSync Migration: Blind Skill Confirmation (Step 6)
Creates `candidate_skills` table and indexes for tracking skill provenance and evidence weights:
- source: 'resume_extracted' | 'self_declared' | 'quiz_verified'
- confidence: 1.0 (experience/quiz), 0.7 (project), 0.2 (self_declared/list)
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

    print(f"[*] Running Blind Skill Confirmation Migration on: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Create candidate_skills table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidate_skills (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            skill        TEXT    NOT NULL,
            source       TEXT    NOT NULL DEFAULT 'self_declared',
            confidence   REAL    DEFAULT 0.2,
            confirmed_at TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, skill)
        )
    """)

    # 2. Create indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_candidate_skills_user ON candidate_skills(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_candidate_skills_skill ON candidate_skills(skill)")

    # 3. Backfill from users.skills where candidate_skills is empty for that user
    users_with_skills = cur.execute("SELECT id, skills FROM users WHERE skills IS NOT NULL AND skills != ''").fetchall()
    backfilled_count = 0
    for uid, s_str in users_with_skills:
        # Check if user already has records in candidate_skills
        existing = cur.execute("SELECT COUNT(*) FROM candidate_skills WHERE user_id=?", (uid,)).fetchone()[0]
        if existing == 0:
            skills = [s.strip() for s in s_str.split(',') if s.strip()]
            for sk in skills:
                try:
                    cur.execute(
                        "INSERT OR IGNORE INTO candidate_skills (user_id, skill, source, confidence) VALUES (?, ?, 'resume_extracted', 0.2)",
                        (uid, sk)
                    )
                    backfilled_count += 1
                except Exception:
                    pass

    conn.commit()
    conn.close()
    print(f"[+] Migration complete. Backfilled {backfilled_count} skills into candidate_skills.")


if __name__ == '__main__':
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    db_file = os.path.join(base_dir, 'instance', 'talentsync.db')
    if not os.path.exists(db_file):
        db_file = os.path.join(base_dir, 'talentsync.db')

    run_migration(db_file)

    backup_db = os.path.join(base_dir, 'talentsync_backup_phase5.db')
    if os.path.exists(backup_db):
        run_migration(backup_db)

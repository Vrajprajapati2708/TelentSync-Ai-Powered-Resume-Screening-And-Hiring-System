"""
Database Migration: Add work_mode and salary_min/max columns and SQLite indexes for Live Jobs Search.
"""
import os
import re
import sqlite3
from typing import Optional
from app.config.settings import ActiveConfig

def run_migration(db_path: Optional[str] = None):
    if not db_path:
        db_path = getattr(ActiveConfig, 'SQLITE_DB_PATH', 'talentsync.db')
        
    print(f"Applying jobs search migration to {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # 1. Check existing columns
    columns = [col[1] for col in cur.execute("PRAGMA table_info(jobs)").fetchall()]

    if 'work_mode' not in columns:
        cur.execute("ALTER TABLE jobs ADD COLUMN work_mode TEXT DEFAULT 'onsite'")
        print("Added column: work_mode")
    if 'salary_min' not in columns:
        cur.execute("ALTER TABLE jobs ADD COLUMN salary_min INTEGER DEFAULT 0")
        print("Added column: salary_min")
    if 'salary_max' not in columns:
        cur.execute("ALTER TABLE jobs ADD COLUMN salary_max INTEGER DEFAULT 0")
        print("Added column: salary_max")

    # 2. Update work_mode and salary ranges from existing data
    rows = cur.execute("SELECT id, location, type, salary, description FROM jobs").fetchall()
    updated = 0
    for jid, loc, jtype, sal, desc in rows:
        loc_s = (loc or '').lower()
        desc_s = (desc or '').lower()
        jtype_s = (jtype or '').lower()
        
        # Determine work_mode
        if 'remote' in loc_s or 'remote' in jtype_s or 'remote' in desc_s or 'work from home' in desc_s or 'wfh' in desc_s:
            mode = 'remote'
        elif 'hybrid' in loc_s or 'hybrid' in desc_s:
            mode = 'hybrid'
        else:
            mode = 'onsite'
            
        # Determine salary_min and salary_max (INR annual)
        # e.g., '12-18 LPA' -> 1200000 to 1800000
        s_min, s_max = 0, 0
        if sal:
            m = re.search(r'(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*lpa', sal, re.I)
            if m:
                s_min = int(float(m.group(1)) * 100000)
                s_max = int(float(m.group(2)) * 100000)
            else:
                m1 = re.search(r'(\d+(?:\.\d+)?)\s*lpa', sal, re.I)
                if m1:
                    s_min = int(float(m1.group(1)) * 100000)
                    s_max = s_min
        
        cur.execute("UPDATE jobs SET work_mode=?, salary_min=?, salary_max=? WHERE id=?", (mode, s_min, s_max, jid))
        updated += 1

    # 3. Create SQLite indexes for fast filtering & search
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_title ON jobs(title)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_work_mode ON jobs(work_mode)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_salary_min ON jobs(salary_min)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")

    conn.commit()
    print(f"Migration completed successfully. Updated {updated} jobs.")
    conn.close()

if __name__ == '__main__':
    run_migration()

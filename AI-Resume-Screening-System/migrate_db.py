import sqlite3
import os

# Use the same DB file the app uses (relative to AI-Resume-Screening-System/)
DB_PATH = 'talentsync.db'
if not os.path.exists(DB_PATH):
    DB_PATH = 'app/database/talentsync.db'

print(f'Using DB: {os.path.abspath(DB_PATH)}')
conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()
cols = [row[1] for row in cur.execute('PRAGMA table_info(users)').fetchall()]
print(f'Existing columns: {cols}')

if 'is_outlier' not in cols:
    cur.execute('ALTER TABLE users ADD COLUMN is_outlier INTEGER DEFAULT 0')
    print('Added is_outlier column')
else:
    print('is_outlier already exists — skipped')

if 'cluster_label' not in cols:
    cur.execute("ALTER TABLE users ADD COLUMN cluster_label TEXT DEFAULT 'Unclustered'")
    print('Added cluster_label column')
else:
    print('cluster_label already exists — skipped')

# Migration for resumes table
cols_resumes = [row[1] for row in cur.execute('PRAGMA table_info(resumes)').fetchall()]
if 'structured_json' not in cols_resumes:
    cur.execute("ALTER TABLE resumes ADD COLUMN structured_json TEXT DEFAULT ''")
    print('Added structured_json column to resumes table')
else:
    print('structured_json already exists in resumes — skipped')

conn.commit()
conn.close()
print('Migration complete. Zero rows deleted.')

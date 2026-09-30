import sqlite3
conn = sqlite3.connect('talentsync.db')
rows = conn.execute("SELECT id, name, email, role FROM users WHERE role='hr'").fetchall()
print("HR Admin accounts found:")
for r in rows:
    print(f"  ID:{r[0]} | Name:{r[1]} | Email:{r[2]} | Role:{r[3]}")
conn.close()

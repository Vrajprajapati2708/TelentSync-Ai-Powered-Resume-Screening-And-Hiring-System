import sqlite3
from werkzeug.security import check_password_hash
conn = sqlite3.connect('talentsync.db')
user = conn.execute("SELECT password FROM users WHERE email='priya@demo.com'").fetchone()
print(check_password_hash(user[0], 'demo123'))

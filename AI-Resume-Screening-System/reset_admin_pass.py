import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

conn = sqlite3.connect('talentsync.db')

# Set a known password for the HR admin
new_password = 'admin@123'
hashed = generate_password_hash(new_password)
conn.execute("UPDATE users SET password=? WHERE email='priya@demo.com'", (hashed,))
conn.commit()

# Verify it works
stored = conn.execute("SELECT password FROM users WHERE email='priya@demo.com'").fetchone()[0]
ok = check_password_hash(stored, new_password)
print(f"Password reset successful: {ok}")
print(f"Email:    priya@demo.com")
print(f"Password: {new_password}")
conn.close()

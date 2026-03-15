import sqlite3

conn = sqlite3.connect('database/auction.db')
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT
)
""")

# Insert default admin
cur.execute("""
INSERT INTO admin (username, password)
VALUES ('admin', 'admin123')
""")

conn.commit()
conn.close()

print("Admin created ✅")
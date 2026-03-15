import sqlite3

conn = sqlite3.connect('auction.db')  # ✅ correct path
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE auctions ADD COLUMN predicted_low REAL")
except sqlite3.OperationalError:
    print("predicted_low column already exists")

try:
    cur.execute("ALTER TABLE auctions ADD COLUMN predicted_high REAL")
except sqlite3.OperationalError:
    print("predicted_high column already exists")

conn.commit()
conn.close()

print("Database update complete.")

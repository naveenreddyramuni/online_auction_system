import sqlite3

conn = sqlite3.connect('database/auction.db')
cur = conn.cursor()

# Add timestamp column
try:
    cur.execute("""
        ALTER TABLE bids
        ADD COLUMN timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    """)
    print("Timestamp column added ✅")
except:
    print("Timestamp column already exists ⚠️")

# Add malicious flag column
try:
    cur.execute("""
        ALTER TABLE bids
        ADD COLUMN is_malicious INTEGER DEFAULT 0
    """)
    print("Malicious flag column added ✅")
except:
    print("Malicious column already exists ⚠️")

conn.commit()
conn.close()

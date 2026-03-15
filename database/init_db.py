import sqlite3

# Connect to database (inside database folder)
conn = sqlite3.connect('auction.db')
cur = conn.cursor()

# USERS TABLE
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# AUCTIONS TABLE (ONLY ONCE ✅)
cur.execute("""
CREATE TABLE IF NOT EXISTS auctions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    starting_price REAL NOT NULL,
    predicted_price REAL,
    final_price REAL,
    end_time TEXT,
    seller_id INTEGER
)
""")

# BIDS TABLE (CORRECTLY NAMED ✅)
cur.execute("""
CREATE TABLE IF NOT EXISTS bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_id INTEGER,
    bidder_id INTEGER,
    bid_amount REAL,
    bid_time TEXT
)
""")

conn.commit()
conn.close()

print("Database initialized successfully.")

import sqlite3

conn = sqlite3.connect('database/auction.db')
cur = conn.cursor()

# USERS TABLE
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    email TEXT,
    password TEXT
)
""")

# AUCTIONS TABLE
cur.execute("""
CREATE TABLE IF NOT EXISTS auctions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT,
    starting_price REAL,
    current_price REAL,
    duration INTEGER,
    category INTEGER,
    market_avg REAL
)
""")

# BIDS TABLE
cur.execute("""
CREATE TABLE IF NOT EXISTS bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_id INTEGER,
    bidder TEXT,
    bid_amount REAL
)
""")

conn.commit()
conn.close()

print("Tables created successfully ✅")

import sqlite3

# Connect to database
conn = sqlite3.connect('database/auction.db')
cur = conn.cursor()

try:
    # Add new column
    cur.execute("""
        ALTER TABLE auctions
        ADD COLUMN predicted_price REAL
    """)
    print("predicted_price column added successfully ✅")

except Exception as e:
    print("Column may already exist ⚠️")
    print(e)

conn.commit()
conn.close()

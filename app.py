from flask import Flask, render_template, request, redirect, session
import sqlite3
import joblib
import numpy as np
import datetime
import smtplib
import random
from email.mime.text import MIMEText
from flask import session

import joblib

price_model = joblib.load("model/price_model.pkl")

category_encoder = joblib.load("model/category_encoder.pkl")

app = Flask(__name__)
app.secret_key = "auction_secret_key"

conn = sqlite3.connect('database/auction.db')
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS bids")

cur.execute("""
CREATE TABLE bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_id INTEGER,
    bidder TEXT,
    bid_amount REAL,
    bid_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("Bids table recreated successfully")


# ---------------- HOME ---------------- #

@app.route('/')
def home():
    return render_template('home.html')


# ---------------- REGISTER ---------------- #

import random

@app.route('/register', methods=['GET','POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        otp = random.randint(100000,999999)

        print("OTP for verification:", otp)

        session['otp'] = str(otp)
        session['username'] = username
        session['email'] = email
        session['password'] = password

        return redirect('/verify_otp')

    return render_template('register.html')


# ---------------- LOGIN ---------------- #

@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('database/auction.db')
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username=? AND password=?",(username,password))

        user = cur.fetchone()

        if user:

            session['username'] = username   # ← THIS IS STEP 3

            return redirect('/dashboard')

        else:
            return "Invalid Login"

    return render_template('login.html')

# ---------------- DASHBOARD ---------------- #

@app.route('/dashboard')
def dashboard():

    if 'username' not in session:
        return redirect('/login')

    return render_template(
        'dashboard.html',
        username=session['username']
    )


# ---------------- LOGOUT ---------------- #

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')


# ---------------- CREATE AUCTION + ML ---------------- #

@app.route('/create_auction', methods=['GET','POST'])
def create_auction():

    if 'username' not in session:
        return redirect('/login')

    if request.method == 'POST':

        product_name = request.form['product_name']
        starting_price = float(request.form['starting_price'])
        duration = int(request.form['duration'])
        category = request.form['category']
        market_avg = float(request.form['market_avg'])
        seller_rating = float(request.form['seller_rating'])

        # initial auction state
        bid_count = 0

        # encode category for ML model
        category_encoded = category_encoder.transform([category])[0]

        # default feature assumptions
        popularity = 1
        condition_score = 1

        # ML feature vector
        features = [[
            starting_price,
            market_avg,
            seller_rating,
            bid_count,
            duration,
            category_encoded,
            popularity,
            condition_score
        ]]

        # ML model prediction
        ml_price = price_model.predict(features)[0]

        # rule-based market estimate
        market_factor = (
            starting_price * 0.4 +
            market_avg * 0.4 +
            seller_rating * 300 +
            duration * 200
        )

        # demand factor
        demand_boost = bid_count * 150

        # hybrid final prediction
        predicted_price = (ml_price * 0.6) + (market_factor * 0.4) + demand_boost

        predicted_price = round(predicted_price,2)

        # auction end time
        end_time = datetime.datetime.now() + datetime.timedelta(days=duration)

        conn = sqlite3.connect('database/auction.db')
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO auctions
        (product_name, starting_price, current_price, duration, category, market_avg, end_time, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,(
            product_name,
            starting_price,
            starting_price,
            duration,
            category,
            market_avg,
            end_time,
            session['username']
        ))

        conn.commit()
        conn.close()

        return render_template(
            "prediction_result.html",
            predicted_price=predicted_price
        )

    return render_template("create_auction.html")
# ---------------- VIEW AUCTIONS ---------------- #

@app.route('/view_auctions')
def view_auctions():

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database/auction.db')
    cur = conn.cursor()

    cur.execute("""
    SELECT a.id,
           a.product_name,
           a.starting_price,
           a.current_price,
           a.duration,
           a.category,
           a.market_avg,
           COALESCE(
               (SELECT username
                FROM bids
                WHERE auction_id = a.id
                ORDER BY bid_amount DESC
                LIMIT 1),
               'No bids yet'
           ) AS highest_bidder
    FROM auctions a
    """)

    auctions = cur.fetchall()

    conn.close()

    return render_template(
        "view_auctions.html",
        auctions=auctions,
        username=session['username']
    )
    


@app.route('/place_bid', methods=['POST'])
def place_bid():

    if 'username' not in session:
        return redirect('/login')

    import sqlite3
    import datetime

    auction_id = int(request.form['auction_id'])
    bid_amount = float(request.form['bid_amount'])
    username = session['username']

    conn = sqlite3.connect('database/auction.db')
    cur = conn.cursor()

    # Get current auction price
    cur.execute("SELECT current_price FROM auctions WHERE id=?", (auction_id,))
    result = cur.fetchone()

    if not result:
        conn.close()
        return redirect('/view_auctions')

    current_price = result[0]

    # Bid must be higher
    if bid_amount <= current_price:
        conn.close()
        return "Bid must be higher than current price"


    suspicious = False
    warning_message = None


    # RULE 1: Bid greater than 3× current price
    if bid_amount > current_price * 3:
        suspicious = True
        warning_message = "⚠ Suspicious Activity: Bid too high compared to current price."


    # RULE 2: Abnormal jump compared to last bid
    cur.execute("""
    SELECT bid_amount FROM bids
    WHERE auction_id=?
    ORDER BY bid_time DESC
    LIMIT 1
    """, (auction_id,))

    last_bid = cur.fetchone()

    if last_bid:
        if bid_amount > last_bid[0] * 2:
            suspicious = True
            warning_message = "⚠ Suspicious Activity: Abnormal bid jump detected."


    # RULE 3: 5 bids within 1 minute
    cur.execute("""
    SELECT COUNT(*) FROM bids
    WHERE username=? AND bid_time > datetime('now','-1 minute')
    """,(username,))

    recent_bid_count = cur.fetchone()[0]

    if recent_bid_count >= 5:
        suspicious = True
        warning_message = "⚠ Suspicious Activity: Too many bids within 1 minute."


    # If suspicious → reject bid
    if suspicious:
        conn.close()
        return warning_message


    # Normal bid → insert bid
    cur.execute("""
    INSERT INTO bids (auction_id, username, bid_amount, bid_time)
    VALUES (?, ?, ?, ?)
    """,(auction_id, username, bid_amount, datetime.datetime.now()))


    # Update auction price
    cur.execute("""
    UPDATE auctions
    SET current_price=?, highest_bidder=?
    WHERE id=?
    """,(bid_amount, username, auction_id))


    conn.commit()
    conn.close()

    return redirect('/view_auctions')

# ---------------- AUCTION DETAIL + BID ---------------- #

@app.route('/auction/<int:auction_id>', methods=['GET', 'POST'])
def auction_detail(auction_id):

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database/auction.db')
    cur = conn.cursor()

    cur.execute("SELECT * FROM auctions WHERE id=?", (auction_id,))
    auction = cur.fetchone()

    message = ""

    if request.method == 'POST':

        bid_amount = float(request.form['bid_amount'])
        current_price = float(auction[3])

        if bid_amount > current_price:

            cur.execute("""
                UPDATE auctions
                SET current_price=?
                WHERE id=?
            """, (bid_amount, auction_id))

            conn.commit()
            message = "✅ Bid placed successfully!"

        else:
            message = "❌ Bid must be higher than current price!"

        cur.execute("SELECT * FROM auctions WHERE id=?", (auction_id,))
        auction = cur.fetchone()

    conn.close()

    return render_template(
        'auction_detail.html',
        auction=auction,
        message=message
    )


def detect_fake_bidder(bidder, auction_id):

    conn = sqlite3.connect('database/auction.db')
    cur = conn.cursor()

    cur.execute("""
    SELECT COUNT(*) FROM bids
    WHERE bidder=? AND auction_id=? 
    AND bid_time >= datetime('now','-1 minute')
    """,(bidder,auction_id))

    bid_count = cur.fetchone()[0]

    conn.close()

    if bid_count > 5:
        return True

    return False

    if detect_fake_bidder(bidder, auction_id):
        return "Suspicious bidding detected. Please wait."
    


@app.route('/delete_auction/<int:auction_id>')
def delete_auction(auction_id):

    if 'username' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database/auction.db')
    cur = conn.cursor()

    cur.execute("DELETE FROM auctions WHERE id=?", (auction_id,))
    cur.execute("DELETE FROM bids WHERE auction_id=?", (auction_id,))

    conn.commit()
    conn.close()

    return redirect('/view_auctions')

def send_otp_email(receiver_email, otp):

    sender_email = "yourgmail@gmail.com"
    sender_password = "your_app_password"

    subject = "Auction System OTP Verification"

    body = f"Your OTP for registration is: {otp}"

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(sender_email, sender_password)
    server.send_message(msg)
    server.quit()


@app.route('/verify_otp', methods=['GET','POST'])
def verify_otp():

    if request.method == 'POST':

        user_otp = request.form['otp']

        if user_otp == session.get('otp'):

            conn = sqlite3.connect('database/auction.db')
            cur = conn.cursor()

            cur.execute("""
            INSERT INTO users(username,email,password)
            VALUES(?,?,?)
            """,(
            session['username'],
            session['email'],
            session['password']
            ))

            conn.commit()
            conn.close()

            return redirect('/login')

        else:
            return "Invalid OTP"

    return render_template('verify_otp.html')
    

import sqlite3

conn = sqlite3.connect("database/auction.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS bids")

cur.execute("""
CREATE TABLE bids(
id INTEGER PRIMARY KEY AUTOINCREMENT,
auction_id INTEGER,
username TEXT,
bid_amount REAL,
bid_time TIMESTAMP
)
""")

conn.commit()
conn.close()

print("Bids table recreated correctly")



@app.route('/suspicious')
def suspicious():

    conn = sqlite3.connect('database/auction.db')
    cur = conn.cursor()

    cur.execute("SELECT * FROM suspicious_bids")

    data = cur.fetchall()

    conn.close()

    return render_template("suspicious.html",data=data)

@app.route('/admin')
def admin_dashboard():

    if 'username' not in session:
        return redirect('/login')

    if session['username'] != 'admin':
        return "Access Denied"

    conn = sqlite3.connect('database/auction.db')
    cur = conn.cursor()

    # total users
    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    # total auctions
    cur.execute("SELECT COUNT(*) FROM auctions")
    auctions = cur.fetchone()[0]

    # total bids
    cur.execute("SELECT COUNT(*) FROM bids")
    bids = cur.fetchone()[0]

    # suspicious bids
    cur.execute("SELECT COUNT(*) FROM suspicious_bids")
    suspicious = cur.fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        users=users,
        auctions=auctions,
        bids=bids,
        suspicious=suspicious
    )


@app.route('/admin_auctions')
def admin_auctions():

    if session.get('username') != "admin":
        return "Access Denied"

    conn = sqlite3.connect('database/auction.db')
    cur = conn.cursor()

    cur.execute("SELECT * FROM auctions")
    auctions = cur.fetchall()

    conn.close()

    return render_template("admin_auctions.html", auctions=auctions)

@app.route('/admin_delete_auction/<int:id>')
def admin_delete_auction(id):

    if session.get('username') != "admin":
        return "Access Denied"

    conn = sqlite3.connect('database/auction.db')
    cur = conn.cursor()

    cur.execute("DELETE FROM auctions WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect('/admin_auctions')

@app.route('/admin_suspicious')
def admin_suspicious():

    if session.get('username') != "admin":
        return "Access Denied"

    conn = sqlite3.connect('database/auction.db')
    cur = conn.cursor()

    cur.execute("SELECT * FROM suspicious_bids")
    data = cur.fetchall()

    conn.close()

    return render_template("admin_suspicious.html", data=data)

import sqlite3

conn = sqlite3.connect("database/auction.db")
cur = conn.cursor()

cur.execute("INSERT INTO users (username,password) VALUES ('admin','admin123')")

conn.commit()
conn.close()

# ---------------- RUN ---------------- #

if __name__ == "__main__":
    app.run(debug=True)
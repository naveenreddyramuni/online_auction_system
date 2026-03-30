from flask import Flask, render_template, request, redirect, session
import sqlite3
import joblib
import numpy as np
import datetime
import smtplib
import random
from flask_mail import Mail, Message
from flask import session
from flask import redirect, url_for
from flask import request

import joblib

price_model = joblib.load("model/price_model.pkl")
category_encoder = joblib.load("model/category_encoder.pkl")

app = Flask(__name__)
app.secret_key = 'super_secret_key'

app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=10)

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


import re

def is_valid_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters"

    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"

    if not re.search(r"[0-9]", password):
        return "Password must contain at least one number"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return "Password must contain at least one special character"

    return None


# ---------------- REGISTER ---------------- #

import random

@app.route('/register', methods=['GET','POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # ✅ STEP 2: ADD PASSWORD VALIDATION HERE
        error = is_valid_password(password)
        if error:
            return error   # or render_template('register.html', error=error)

        # 🔽 OTP logic (keep same)
        otp = random.randint(100000,999999)

        print("OTP for verification:", otp)
        send_otp(email, otp) 

        session['otp'] = str(otp)
        session['username'] = username
        session['email'] = email
        session['password'] = password

        return redirect('/verify_page')

    return render_template('register.html')


def send_winner_email(to_email, auction_title, amount):
    msg = Message(
        'Auction Won!',
        sender=app.config['MAIL_USERNAME'],
        recipients=[to_email]
    )
    msg.body = f"You won {auction_title} for ₹{amount}"
    mail.send(msg)


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

    import datetime
    import sqlite3
    import pickle

    if request.method == 'POST':

        product_name = request.form['product_name']
        starting_price = float(request.form['starting_price'])
        duration = int(request.form['duration'])
        category_text = request.form['category']

        category_map = {
            "Electronics": 1,
            "Furniture": 2,
            "Vehicle": 3,
            "Real Estate": 4,
            "Antiques": 5
        }

        category = category_map.get(category_text, 0)
        market_avg = float(request.form['market_avg'])

        # 🔥 PREDICT PRICE BEFORE INSERT
        try:
            model = pickle.load(open('model.pkl', 'rb'))
            predicted_price = model.predict([[starting_price, category, market_avg]])[0]
        except:
            predicted_price = market_avg   # fallback

        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(days=duration)

        conn = sqlite3.connect('database/auction.db')
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO auctions 
        (product_name, starting_price, current_price, duration, category, market_avg, predicted_price, highest_bidder, end_time, email_sent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_name,
            starting_price,
            starting_price,
            duration,
            category,
            market_avg,
            float(predicted_price),   # ✅ STORED HERE
            "No bids yet",
            end_time,
            0
        ))

        conn.commit()
        conn.close()

        return render_template('prediction_result.html', predicted_price=predicted_price)

    return render_template('create_auction.html')







# ---------------- VIEW AUCTIONS ---------------- #

@app.route('/view_auctions')
def view_auctions():

    import datetime
    import sqlite3
    from flask import request   # ✅ ADDED (important for highlight)

    conn = sqlite3.connect('database/auction.db')
    cur = conn.cursor()

    cur.execute("SELECT * FROM auctions")
    auctions = cur.fetchall()

    highlight_id = request.args.get('highlight_id')

    for auction in auctions:

        try:
            end_time_value = auction[8]

            if end_time_value is None:
                continue

            if isinstance(end_time_value, str):
                end_time = datetime.datetime.fromisoformat(end_time_value)
            else:
                end_time = end_time_value

            remaining = end_time - datetime.datetime.now()

            if remaining.total_seconds() <= 0:

                cur.execute("""
                SELECT highest_bidder, current_price, product_name, email_sent
                FROM auctions WHERE id=?
                """, (auction[0],))

                result = cur.fetchone()

                # ✅ ONLY SEND IF NOT SENT BEFORE
                if result and result[0] != "No bids yet" and result[3] == 0:

                    winner = result[0]
                    amount = result[1]
                    title = result[2]

                    # ✅ GET WINNER EMAIL
                    cur.execute("SELECT email FROM users WHERE username=?", (winner,))
                    user = cur.fetchone()

                    if user:
                        print(f"Sending email to {user[0]} for auction {title}")  # ✅ DEBUG

                        send_winner_email(user[0], title, amount)

                        # ✅ MARK EMAIL SENT
                        cur.execute("UPDATE auctions SET email_sent=1 WHERE id=?", (auction[0],))
                        conn.commit()

        except Exception as e:
            print("Error:", e)

    conn.close()

    return render_template("view_auctions.html", auctions=auctions, highlight_id=highlight_id)

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
    if not suspicious:
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
    if not suspicious:
        cur.execute("""
        SELECT COUNT(*) FROM bids
        WHERE username=? AND bid_time > datetime('now','-1 minute')
        """,(username,))

        recent_bid_count = cur.fetchone()[0]

        if recent_bid_count >= 5:
            suspicious = True
            warning_message = "⚠ Suspicious Activity: Too many bids within 1 minute."


    # FINAL CHECK
    if suspicious:
        conn.close()
        return warning_message


    # ✅ INSERT BID
    cur.execute("""
    INSERT INTO bids (auction_id, username, bid_amount, bid_time)
    VALUES (?, ?, ?, ?)
    """,(auction_id, username, bid_amount, datetime.datetime.now()))


    # ✅ UPDATE PRICE + HIGHEST BIDDER (MAIN FIX)
    cur.execute("""
    UPDATE auctions
    SET current_price = ?, highest_bidder = ?
    WHERE id = ?
    """,(bid_amount, username, auction_id))


    # ✅ COMMIT (VERY IMPORTANT)
    conn.commit()
    conn.close()

    return redirect(f'/view_auctions?highlight_id={auction_id}')

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

from flask import Flask, render_template, request, session
from flask_mail import Mail, Message
import random
import datetime

#app = Flask(__name__)
#app.secret_key = 'secret123'

# ✅ Gmail SMTP (App Password required)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'naveenreddyramuni@gmail.com'      # 🔁 replace
app.config['MAIL_PASSWORD'] = 'duxgbofpbkwyojzz'         # 🔁 replace

mail = Mail(app)

# 🔢 Generate OTP
def generate_otp():
    return str(random.randint(100000, 999999))

# 📧 Send OTP
def send_otp(email, otp):
    try:
        msg = Message(
            'OTP Verification',
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f'Your OTP is: {otp}'

        mail.send(msg)
        print("Email sent successfully ✅")

    except Exception as e:
        print("Email sending failed ❌:", e)

# 🏠 MAIN PAGE (your existing page — DO NOT CHANGE)
#@app.route('/')
#def home():
    #return render_template('home.html')

# 🔐 OTP PAGE (new page)
@app.route('/otp')
def otp_page():
    return render_template('index.html')

# 📤 SEND OTP (POST only)


def send_winner_email(to_email, auction_title, amount):
    try:
        msg = Message(
            subject="🎉 Congratulations! You Won the Auction",
            sender=app.config['MAIL_USERNAME'],
            recipients=[to_email]
        )

        msg.body = f"""
Congratulations! 🎉

You have successfully won the auction: {auction_title}

Winning Amount: ₹{amount}

Please login to your account for further details.

Thank you for using Smart Auction System 🚀
        """

        mail.send(msg)
        print("Winner email sent successfully ✅")

    except Exception as e:
        print("Email error ❌:", e)


@app.route('/verify_otp', methods=['POST'])
def verify_otp():

    import datetime
    import sqlite3

    if 'otp' not in session:
        return "Session expired ❌"

    user_otp = request.form['otp']
    stored_otp = session['otp']

    if user_otp != stored_otp:
        return "Invalid OTP ❌"

    # ✅ OTP correct → NOW SAVE USER IN DB

    username = session['username']
    email = session['email']
    password = session['password']

    conn = sqlite3.connect('database/auction.db')
    cur = conn.cursor()

    # check if user already exists
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    existing = cur.fetchone()

    if existing:
        conn.close()
        return "User already exists ❌"

    # insert user
    cur.execute("""
    INSERT INTO users (username, email, password)
    VALUES (?, ?, ?)
    """, (username, email, password))

    conn.commit()
    conn.close()

    # clear session OTP
    session.pop('otp', None)

    return redirect('/login')

@app.route('/verify_page')
def verify_page():
    print("SESSION:", session)   # 👈 check this

    if 'otp' not in session:
        return "Please request OTP first ❌"

    return render_template('verify.html')

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

conn = sqlite3.connect('database/auction.db')
cur = conn.cursor()

cur.execute("SELECT id, highest_bidder FROM auctions")
rows = cur.fetchall()

for row in rows:
    print(row)

conn.close()




import sqlite3

conn = sqlite3.connect('database/auction.db')
cur = conn.cursor()

cur.execute("PRAGMA table_info(auctions);")
columns = cur.fetchall()

for col in columns:
    print(col)

conn.close()

# ---------------- RUN ---------------- #

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

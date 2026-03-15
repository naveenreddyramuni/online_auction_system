# Online Auction System with Price Prediction

## 📌 Project Overview

This project is a **web-based online auction system** integrated with a **Machine Learning model** that predicts the expected auction price of items.
Users can list items for auction, place bids, and view predicted prices based on historical auction data.

The system is built using **Python, Flask, and Machine Learning techniques** to improve auction decision-making.

---

## 🚀 Features

* User registration and login
* Admin panel for auction management
* Item listing for auctions
* Bidding system
* Machine Learning price prediction
* Dataset-based training
* Auction database management
* Web interface using HTML/CSS

---

## 🧠 Machine Learning Model

The price prediction model is trained using historical auction data.

Algorithm used:

* Random Forest Regressor

The model predicts the expected auction price based on:

* Item category
* Base price
* Number of bids
* Auction duration

---

## 🗂 Project Structure

Auction_System

├── app.py
├── train_model.py
├── generate_dataset.py
├── auction_dataset.csv
├── auction.db
├── model/
├── templates/
├── static/
├── database/
└── README.md

---

## ⚙️ Technologies Used

Backend:

* Python
* Flask

Machine Learning:

* Scikit-Learn
* Pandas
* NumPy

Frontend:

* HTML
* CSS
* Bootstrap

Database:

* SQLite

---

## 📊 Dataset

The dataset contains historical auction records including:

* Item name
* Category
* Base price
* Number of bids
* Final auction price

Dataset size: **1000+ auction samples**

---

## ▶️ How to Run the Project

1. Clone the repository

git clone https://github.com/yourusername/Auction-System.git

2. Navigate to project folder

cd Auction-System

3. Install dependencies

pip install -r requirements.txt

4. Run the application

python app.py

5. Open browser

http://127.0.0.1:5000

---

## 🎯 Future Improvements

* Email notifications
* AI-based bidding recommendations
* Secure payment integration

---

## 👨‍💻 Author

Naveen Reddy Ramuni
B.Tech CSE (IoT)

---

## ⭐ If you like this project

Give it a star on GitHub!

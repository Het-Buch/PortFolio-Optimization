import requests
import firebase_admin
from firebase_admin import auth, db
try:
    import yfinance as yf
except ImportError:
    pass
from datetime import datetime
from database.connection import initialize_firebase
from dotenv import load_dotenv
import os


# Ensure Firebase is initialized
initialize_firebase()

API_KEY = os.getenv("API_KEY")


def get_user_details(user_id):
    try:
        # Fetch user details from Firebase Realtime Database
        users_ref = db.reference("users")
        user_data = users_ref.child(user_id).child("personal").get()

        # print(users_ref.child(user_id).child("personal").get())
        
        user_details = {
            "email": user_data.get("email"),
            "name": user_data.get("name"),
            "phone": user_data.get("phone")
        }

        return user_details

    except Exception as e:
        # print(f"Error fetching user details: {e}")
        return None
    
def get_stocks_from_db():
    try:
        # Reference to the database path
        ref = db.reference("stocks")

        # Fetch all stocks ordered by stock_id
        stocks = ref.get()

        return stocks if stocks else {}
    except Exception as e:
        print(f"Error fetching stocks: {e}")
        return None
    
def generate_purchase_id():
    try:
        # Reference to the database path
        ref = db.reference("purchases")

        # Check if the "purchases" reference exists, if not, create it
        if not ref.get():
            ref.set({})

        # Fetch all purchases ordered by purchase_id
        purchases = ref.get()

        if purchases:
            last_purchase_id = max(purchases.keys())  
            last_number = int(last_purchase_id[3:])
        else:
            last_number = 0  # Start from 1 if no purchases exist

        # Generate new purchase ID
        new_number = last_number + 1

        year_suffix = datetime.now().year % 100  # Get the last two digits of the current year

        purchase_id = f"{year_suffix}p{new_number:07d}"  # Format: 24p0000001

        return purchase_id

    except Exception as e:
        print(f"Error generating purchase ID: {e}")
        return None
    
def add_purchase_to_db(user_id, company_name, quantity, price_per_stock, total_cost,stock_id,ticker):
    try:
        # Reference to the database path
        ref = db.reference("purchases")

        # Generate unique purchase ID
        purchase_id = generate_purchase_id()

        # Store purchase data in Realtime Database
        ref.child(purchase_id).set({
            "user_id": user_id,
            "company_name": company_name,
            "quantity": quantity,
            "price_per_stock": price_per_stock,
            "total_cost": total_cost,
            "purchase_id": purchase_id,
            "purchased_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "purchased_by": user_id,  # There may be possiblity manager will purhcase the stock for user
            "sold": False,
            "updated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_by": user_id,  # Manager can sell the stock for user
            "ticker": ticker,
            "stock_id":stock_id,
            "sold_at":0.0,
        })

        return True
    except Exception as e:
        print(f"Error adding purchase: {e}")
        return False

def get_purchased_stocks(user_id):
    try:
        ref = db.reference("purchases")
        all_purchases = ref.get() or {}
        portfolio = {}
        for purchase_id, purchase in all_purchases.items():
            if purchase.get("user_id") != user_id or purchase.get("sold"):
                continue
            stock_id = purchase.get("stock_id")
            if stock_id not in portfolio:
                portfolio[stock_id] = {
                    "company_name": purchase.get("company_name"),
                    "ticker": purchase.get("ticker"),
                    "quantity": 0,
                    "total_cost": 0
                }
            portfolio[stock_id]["quantity"] += purchase.get("quantity", 0)
            portfolio[stock_id]["total_cost"] += purchase.get("total_cost", 0)
        return portfolio
    except Exception as e:
        print(f"Error fetching user purchases: {e}")
        return {}
    
def get_stock_data(stock_id):
    try:
        # Reference to the database path
        ref = db.reference("purchases")

        # Fetch stock data for the given stock_id
        stock_data = ref.child(stock_id).get()

        return stock_data if stock_data else {}
    except Exception as e:
        print(f"Error fetching stock data: {e}")
        return None

def update_stock_data(purchased_id, price_per_stock, quantity, user_id):
    try:

        if quantity <= 0:
            print("Quantity must be greater than 0.")
            return False
        else:
            # Reference to the database path
            ref = db.reference("purchases")

            # Update stock data for the given stock_id
            ref.child(purchased_id).update({
                "quantity": quantity,
                "total_cost": price_per_stock * quantity,
                "updated_by": user_id,  # Assuming the user ID is the same as stock_id for simplicity
                "updated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

            return True
    except Exception as e:
        print(f"Error updating stock data: {e}")
        return False
    
def sell_stock(purchased_id, user_id,current_price):
    try:
        # Reference to the database path
        ref = db.reference("purchases")

        # Update stock data for the given stock_id to mark it as sold
        ref.child(purchased_id).update({
            "sold": True,
            "sold_at":current_price,
            "updated_by": user_id,
            "updated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        return True
    except Exception as e:
        print(f"Error selling stock: {e}")
        return False

def get_live_price_from_db(ticker):
    try:
        # Fetch live price using yfinance
        stock = yf.Ticker(ticker)
        live_price = stock.history(period="1m")

        return live_price
    except Exception as e:
        print(f"Error fetching live price: {e}")
        return 0.0


if __name__ == "__main__":
    get_user_details()
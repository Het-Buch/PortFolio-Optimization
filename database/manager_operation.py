from firebase_admin import db
from database.connection import initialize_firebase
from datetime import datetime
from dotenv import load_dotenv
import os

try:  # real init happens in main.py; never fail at import
    initialize_firebase()
except Exception:
    pass
load_dotenv()
API_KEY = os.getenv("API_KEY")

def generate_stock_id():
    n = db.reference("counters/stocks").transaction(lambda cur: (cur or 0) + 1)
    return f"{datetime.now().year % 100}s{int(n):07d}"

def stock_exists(stock_ticker):
    try:
        ref = db.reference("stocks")
        stocks = ref.get()

        if stocks:
            for stock in stocks.values():
                if stock.get("ticker") == stock_ticker and not stock.get("is_deleted", False):
                    return True

        return False

    except Exception as e:
        print(f"Error checking stock: {e}")
        return False

def add_stock_to_db(stock_name, stock_ticker, stock_price=0.0, sector="Unknown"):
    try:

        # Check if stock already exists
        if stock_exists(stock_ticker):
            print("Stock already exists")
            return False

        stocks_ref = db.reference("stocks")

        stock_id = generate_stock_id()

        stocks_ref.child(stock_id).set({
            "name": stock_name,
            "ticker": stock_ticker,
            "price": float(stock_price or 0),
            "sector": str(sector or "Unknown").strip() or "Unknown",
            "stock_id": stock_id,
            "is_deleted": False,
            "updated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_by": "manager",
            "added_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "added_by": "manager",
        })

        return True

    except Exception as e:
        print(f"Error adding stock: {e}")
        return False


def get_all_stocks_from_db():
    try:
        # Reference to the database path
        ref = db.reference("stocks")

        # Fetch all stocks ordered by stock_id
        stocks = ref.get()

        if not stocks:
            return {}

        stocks = {k: v for k, v in stocks.items() if not (v or {}).get("is_deleted", False)}
        for stock in stocks.values():
            stock["sector"] = str(stock.get("sector", "Unknown") or "Unknown").strip() or "Unknown"

        return stocks
    except Exception as e:
        print(f"Error fetching stocks: {e}")
        return None

def get_users():
    try:
        # Reference to the database path
        ref = db.reference("users")

        # Fetch all users ordered by user_id
        users = ref.get()

        return users if users else {}
    except Exception as e:
        print(f"Error fetching users: {e}")
        return None  

def get_users_first_login():
    
    try:
        # Reference to the database path
        ref = db.reference("users")

        # Fetch all users ordered by user_id
        users = ref.get()

        if users:
            user_data=[]
            # Select specific details like email and username
            for user in users.values():
                save={}
                save["username"]=user.get("personal", {}).get("user_id")
                save["first_login"]=user.get("login", {}).get("first_login_date")
                user_data.append(save)
                
            return user_data
        else:
            return None

    except Exception as e:
        print(f"Error fetching users: {e}")
        return None 

def get_user_purchases_over_time(): 
    try:
        # Reference to the database path
        ref = db.reference("purchases")

        # Fetch all users ordered by user_id
        purhcase = ref.get()

        if not purhcase:
            return None
        else:
            purchase_data=[]
            # Select specific details like company name, purchase date, and qunatity
            for purchase in purhcase.values():
                save={}
                save["company_name"]=purchase.get("company_name")
                save["purchase_date"]=purchase.get("purchased_on")
                save["quantity"]=purchase.get("quantity")
                purchase_data.append(save)
            
                
            return purchase_data

    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def delete_stock_from_db(stock_id):
    try:
        # Reference to the database path
        ref = db.reference("stocks")

        # Check if the stock exists
        stock = ref.child(stock_id).get()
        if not stock:
            return False  # Stock not found

        # Mark the stock as deleted (soft delete)
        ref.child(stock_id).update({
            "is_deleted": True,
            "updated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_by": "manager"  # Assuming the manager is deleting the stock
        })

        return True
    except Exception as e:
        print(f"Error deleting stock: {e}")
        return False
    
def get_stock_data(stock_id):
    try:
        # Reference to the database path
        ref = db.reference("stocks")

        # Fetch stock data by stock_id
        stock_data = ref.child(stock_id).get()
        return stock_data if stock_data else {}
    except Exception as e:
        print(f"Error fetching stock data: {e}")
        return None
    
def update_stock_data(stock_id, stock_name, stock_ticker, stock_price, user_id, sector="Unknown"):
    try:
        # Reference to the database path
        ref = db.reference("stocks")

        # Check if the stock exists
        stock = ref.child(stock_id).get()
        if not stock:
            return False  # Stock not found

        # Update the stock data
        ref.child(stock_id).update({
            "name": stock_name,
            "ticker": stock_ticker,
            "price": stock_price,
            "sector": str(sector or "Unknown").strip() or "Unknown",
            "updated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_by": user_id  
        })

        return True
    except Exception as e:
        print(f"Error updating stock: {e}")
        return False
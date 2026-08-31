import requests

import firebase_admin

from firebase_admin import auth, db

from datetime import datetime

from database.connection import initialize_firebase

from dotenv import load_dotenv

import os





# Ensure Firebase is initialized

try:  # real init happens in main.py; never fail at import
    initialize_firebase()
except Exception:
    pass



API_KEY = os.getenv("API_KEY")





def _can_modify_purchase(stock_data, user_id):

    owner_id = str((stock_data or {}).get("user_id", "")).strip()

    actor_id = str(user_id or "").strip()

    return bool(owner_id and actor_id and owner_id == actor_id and actor_id != "manager")





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

    

def _rows_for_user(path, user_id):

    """One user's rows. Indexed query; falls back to a full scan without the rule."""

    ref = db.reference(path)

    try:

        return ref.order_by_child("user_id").equal_to(user_id).get() or {}

    except Exception as e:

        # No .indexOn rule yet -- correct but downloads the whole table.

        print(f"{path}: unindexed scan ({e}); add .indexOn user_id to the rules")

        return {k: v for k, v in (ref.get() or {}).items()

                if (v or {}).get("user_id") == user_id}


def _next_id(counter, prefix):

    """Atomic counter. Read-max-increment let two concurrent writes collide."""

    n = db.reference(f"counters/{counter}").transaction(lambda cur: (cur or 0) + 1)

    return f"{datetime.now().year % 100}{prefix}{int(n):07d}"





def generate_purchase_id():

    return _next_id("purchases", "p")





def generate_transaction_id():

    return _next_id("transactions", "t")





def add_transaction_to_db(user_id, purchased_id, company_name, ticker, quantity, price_per_stock, action, mode):

    try:

        ref = db.reference("transactions")

        transaction_id = generate_transaction_id()



        if not transaction_id:

            return False



        total_value = round(float(quantity) * float(price_per_stock), 2)



        ref.child(transaction_id).set({

            "transaction_id": transaction_id,

            "user_id": user_id,

            "purchase_id": purchased_id,

            "company_name": company_name,

            "ticker": ticker,

            "quantity": int(quantity),

            "price_per_stock": float(price_per_stock),

            "total_value": total_value,

            "action": action,

            "mode": mode,

            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

        })



        return True

    except Exception as e:

        print(f"Error adding transaction: {e}")

        return False

    

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

            "target_price": 0.0,

            "target_set": False,

        })



        add_transaction_to_db(

            user_id=user_id,

            purchased_id=purchase_id,

            company_name=company_name,

            ticker=ticker,

            quantity=quantity,

            price_per_stock=price_per_stock,

            action="BUY",

            mode="manual"

        )



        return True

    except Exception as e:

        print(f"Error adding purchase: {e}")

        return False



def get_purchased_stocks(user_id):

    try:



        stocks_ref = db.reference("stocks")

        all_purchases = _rows_for_user("purchases", user_id)

        all_stocks = stocks_ref.get() or {}



        def normalize_sector(value):

            text = str(value or "").strip()

            if not text or text.lower() in {"none", "null", "nan", "n/a", "na", "unknown"}:

                return "Unknown"

            return text



        stock_sector_map = {

            sid: normalize_sector((s or {}).get("sector", "Unknown"))

            for sid, s in all_stocks.items()

        }



        ticker_sector_map = {

            str((s or {}).get("ticker", "")).strip().upper(): normalize_sector((s or {}).get("sector", "Unknown"))

            for s in all_stocks.values()

            if str((s or {}).get("ticker", "")).strip()

        }



        portfolio = {}

        for purchase_id, purchase in all_purchases.items():

            if purchase.get("user_id") != user_id or purchase.get("sold"):

                continue



            stock_id = purchase.get("stock_id")

            ticker = str(purchase.get("ticker", "")).strip().upper()

            sector = stock_sector_map.get(stock_id, "Unknown")

            if sector == "Unknown" and ticker:

                sector = ticker_sector_map.get(ticker, "Unknown")



            portfolio[purchase_id] = {

                "purchase_id": purchase_id,

                "stock_id": stock_id,

                "company_name": purchase.get("company_name"),

                "ticker": purchase.get("ticker"),

                "sector": sector,

                "quantity": purchase.get("quantity", 0),

                "price_per_stock": purchase.get("price_per_stock", 0),

                "total_cost": purchase.get("total_cost", 0),

                "target_price": float(purchase.get("target_price", 0) or 0),

                "target_set": bool(purchase.get("target_set", False)),

                "sold": bool(purchase.get("sold", False)),

            }



        return portfolio

    except Exception as e:

        print(f"Error fetching user purchases: {e}")

        return {}

    

def get_stock_data(purchased_id):

    try:

        # Reference to the database path

        ref = db.reference("purchases")



        # Fetch stock data for the given purchase id

        stock_data = ref.child(purchased_id).get()



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



            stock_data = ref.child(purchased_id).get()

            if not stock_data or stock_data.get("sold", False):

                return False



            if not _can_modify_purchase(stock_data, user_id):

                print("Unauthorized update attempt blocked.")

                return False



            ref.child(purchased_id).update({
                "quantity": quantity,
                "price_per_stock": price_per_stock,
                "total_cost": price_per_stock * quantity,
                "updated_by": user_id,

                "updated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

            })



            return True

    except Exception as e:

        print(f"Error updating stock data: {e}")

        return False

    

def sell_stock(purchased_id, user_id, current_price, mode="manual"):

    try:

        # Reference to the database path

        ref = db.reference("purchases")



        stock_data = ref.child(purchased_id).get()

        if not stock_data or stock_data.get("sold", False):

            return False



        if not _can_modify_purchase(stock_data, user_id):

            print("Unauthorized sell attempt blocked.")

            return False



        quantity = int(stock_data.get("quantity", 0) or 0)

        company_name = stock_data.get("company_name", "")

        ticker = stock_data.get("ticker", "")



        # Update stock data for the given stock_id to mark it as sold

        ref.child(purchased_id).update({

            "sold": True,

            "sold_at": current_price,

            "target_set": False,

            "updated_by": user_id,

            "updated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

        })



        add_transaction_to_db(

            user_id=user_id,

            purchased_id=purchased_id,

            company_name=company_name,

            ticker=ticker,

            quantity=quantity,

            price_per_stock=current_price,

            action="SELL",

            mode=mode

        )



        return True

    except Exception as e:

        print(f"Error selling stock: {e}")

        return False



def get_live_price_from_db(ticker):

    try:

        import yfinance as yf  # lazy: heavy import, rarely used

        stock = yf.Ticker(ticker)

        live_price = stock.history(period="1d")



        return live_price

    except Exception as e:

        print(f"Error fetching live price: {e}")

        return 0.0





def set_target_price(purchased_id, target_price, user_id):

    try:

        if target_price <= 0:

            print("Target price must be greater than 0.")

            return False



        ref = db.reference("purchases")

        stock_data = ref.child(purchased_id).get()



        if not stock_data or stock_data.get("sold", False):

            return False



        if not _can_modify_purchase(stock_data, user_id):

            print("Unauthorized target update attempt blocked.")

            return False



        ref.child(purchased_id).update({

            "target_price": float(target_price),

            "target_set": True,

            "updated_by": user_id,

            "updated_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

        })



        return True

    except Exception as e:

        print(f"Error setting target price: {e}")

        return False





def get_user_transactions(user_id):

    try:

        all_transactions = _rows_for_user("transactions", user_id)



        records = []

        for _, txn in all_transactions.items():

            if txn.get("user_id") != user_id:

                continue



            records.append({

                "timestamp": txn.get("timestamp", ""),

                "action": txn.get("action", ""),

                "mode": txn.get("mode", ""),

                "company_name": txn.get("company_name", ""),

                "ticker": txn.get("ticker", ""),

                "quantity": int(txn.get("quantity", 0) or 0),

                "price_per_stock": float(txn.get("price_per_stock", 0) or 0),

                "total_value": float(txn.get("total_value", 0) or 0),

                "transaction_id": txn.get("transaction_id", ""),

                "purchase_id": txn.get("purchase_id", ""),

            })



        records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return records

    except Exception as e:

        print(f"Error fetching transaction history: {e}")

        return []





if __name__ == "__main__":

    get_user_details()
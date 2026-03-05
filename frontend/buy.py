import streamlit as st
from services.cache import cached_stocks, cached_portfolio
from database.curd import add_purchase_to_db
from services.stock_services import fetch_stock_data

def buy():

    # Check login first
    if "user" not in st.session_state:
        st.warning("You are not logged in. Please login first.")
        st.session_state["page"] = "login"
        st.rerun()
        return

    st.title("Buy Stocks")

    if st.button("Back to Home"):
        st.session_state["page"] = "home"
        st.rerun()

    stock_data = cached_stocks()

    if not stock_data:
        st.warning("No stocks available.")
        return

    # Filter active stocks
    active_stocks = {
        k: v for k, v in stock_data.items()
        if not v.get("is_deleted", False)
    }

    if not active_stocks:
        st.warning("No active stocks available.")
        return

    company_names = sorted(v["name"] for v in active_stocks.values())

    st.subheader("Purchase Stocks")

    company_name = st.selectbox("Select Company", company_names, index=None, placeholder="Choose a stock")

    quantity = st.number_input(
        "Enter quantity",
        min_value=1,
        step=1
    )

    selected_stock = next(
        (v for v in active_stocks.values() if v["name"] == company_name),
        None
    )

    if not selected_stock:
        st.error("Stock not found.")
        return

    ticker = str(selected_stock["ticker"]).strip().upper()
    stock_id = selected_stock["stock_id"]
    # fetch live price
    data = fetch_stock_data([ticker])
    ticker_ns = ticker if ticker.endswith(".NS") else ticker + ".NS"
    live_price = round((data or {}).get(ticker_ns, (data or {}).get("price", 0)) or 0, 2)
    fallback_price = round(float(selected_stock.get("price", 0) or 0), 2)
    price = live_price or fallback_price

    if price == 0:
        st.error("Unable to fetch live stock price.")
        return

    if live_price == 0 and fallback_price > 0:
        st.warning(f"Live price unavailable. Using last saved price: ₹{fallback_price}")

    st.info(f"Live Price per stock: ₹{price}")
    
    col1, col2 = st.columns(2)
    with col1:

        if st.button("Purchase"):

            if quantity <= 0:
                st.error("Quantity must be greater than 0.")
                return

            total_cost = round(quantity * price, 2)

            success = add_purchase_to_db(
                user_id=st.session_state["user"],
                company_name=company_name,
                quantity=quantity,
                price_per_stock=price,
                total_cost=total_cost,
                stock_id=stock_id,
                ticker=ticker,
            )

            if success:
                cached_portfolio.clear()
                st.toast(f"Purchased {quantity} stocks of {company_name}")
                st.rerun()
            else:
                st.error("Purchase failed.")

    with col2:

        if st.button("Home"):
            st.session_state["page"] = "home"
            st.rerun()


if __name__ == "__main__":
    buy()
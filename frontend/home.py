import streamlit as st
import pandas as pd
from services.cache import cached_user, cached_portfolio
from services.stock_services import fetch_stock_data
from database.curd import sell_stock

def home():

    if "user" not in st.session_state:
        st.warning("You are not logged in.")
        st.session_state["page"] = "login"
        st.rerun()
        return

    user_id = st.session_state["user"]

    user_details = cached_user(user_id)
    name = user_details.get("name")

    st.title(f"Hi, {name} 👋")
    st.write("Welcome to the Portfolio Management System!")

    st.sidebar.title("Navigation")

    if st.sidebar.button("Buy New"):
        st.session_state.page = "buy"
        st.rerun()

    if st.sidebar.button("Optimize"):
        st.session_state.page = "optimize"
        st.rerun()

    if st.sidebar.button("Profile"):
        st.session_state.page = "profile"
        st.rerun()

    if st.sidebar.button("Logout"):
        del st.session_state["user"]
        st.session_state.page = "landing"
        st.rerun()

    st.divider()

    purchased = cached_portfolio(user_id)

    if not purchased:
        st.info("No stocks purchased yet.")
        return

    active_stocks = {
        k: v for k, v in purchased.items() if not v.get("sold", False)
    }

    if not active_stocks:
        st.info("No active stocks.")
        return

    stock_data = []
    total_cost = 0

    for stock in active_stocks.values():
        ticker = stock.get("ticker")
        live_price = 0

        if ticker:
            data = fetch_stock_data(ticker)

            if data and "price" in data:
                live_price = round(data["price"], 2)
            else:
                live_price = 0
        quantity = stock.get("quantity", 0)
        total = quantity * live_price
        stock_data.append([
            stock["company_name"],
            quantity,
            live_price,
            round(total, 2)
        ])
        total_cost += total

    df = pd.DataFrame(
        stock_data,
        columns=["Company", "Quantity", "Price", "Total"]
    )

    df.index = df.index + 1

    st.write(f"Total Stocks: {len(df)}")
    st.write(f"Total Investment: ₹{total_cost:.2f}")

    st.dataframe(df, width='stretch')

    st.divider()

    stock_map = {
        v["company_name"]: (k, v)
        for k, v in active_stocks.items()
    }

    selected = st.selectbox(
        "Select Stock",
        list(stock_map.keys())
    )

    stock_id, stock = stock_map[selected]

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Edit"):
            st.session_state.selected_stock = stock_id
            st.session_state.page = "edit_stock"
            st.rerun()

    with col2:
        if st.button("Sell"):

            success = sell_stock(
                stock_id,
                user_id,
                stock["price_per_stock"]
            )

            if success:
                cached_portfolio.clear()
                st.toast("Stock sold successfully")
                st.rerun()
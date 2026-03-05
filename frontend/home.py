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

    grouped_stocks = {}
    for purchase_id, stock in active_stocks.items():
        group_key = stock.get("stock_id") or stock.get("ticker") or purchase_id
        if group_key not in grouped_stocks:
            grouped_stocks[group_key] = {
                "company_name": stock.get("company_name", ""),
                "ticker": stock.get("ticker", ""),
                "quantity": 0,
                "total_cost": 0.0,
                "target_set": False,
                "target_price": 0.0,
                "purchase_ids": []
            }

        grouped_stocks[group_key]["quantity"] += int(stock.get("quantity", 0) or 0)
        grouped_stocks[group_key]["total_cost"] += float(stock.get("total_cost", 0) or 0)
        grouped_stocks[group_key]["purchase_ids"].append(purchase_id)

        stock_target_set = bool(stock.get("target_set", False))
        stock_target_price = float(stock.get("target_price", 0) or 0)
        if stock_target_set and stock_target_price > 0:
            grouped_stocks[group_key]["target_set"] = True
            if grouped_stocks[group_key]["target_price"] == 0:
                grouped_stocks[group_key]["target_price"] = stock_target_price

    stock_data = []
    display_prices = {}
    total_cost = 0
    auto_sold = []

    for stock_key, stock in grouped_stocks.items():
        ticker = str(stock.get("ticker", "")).strip().upper()
        market_price = 0

        if ticker:
            data = fetch_stock_data(ticker)
            ticker_ns = ticker if ticker.endswith(".NS") else ticker + ".NS"
            if data:
                market_price = round(data.get(ticker_ns, data.get("price", 0)) or 0, 2)

        quantity = int(stock.get("quantity", 0) or 0)
        stored_price = float(stock.get("total_cost", 0) or 0) / quantity if quantity > 0 else 0
        derived_price = float(stock.get("total_cost", 0) or 0) / quantity if quantity > 0 else 0
        avg_buy_price = round(stored_price or derived_price, 2)
        sell_check_price = round(market_price or avg_buy_price, 2)
        display_prices[stock_key] = sell_check_price

        target_price = round(float(stock.get("target_price", 0) or 0), 2)
        target_set = bool(stock.get("target_set", False))

        if target_set and target_price > 0 and sell_check_price > 0 and sell_check_price >= target_price:
            sold_any = False
            for purchase_id in stock.get("purchase_ids", []):
                if sell_stock(purchase_id, user_id, sell_check_price, mode="auto"):
                    sold_any = True

            if sold_any:
                auto_sold.append(f"{stock.get('company_name', 'Stock')} @ ₹{sell_check_price}")
                continue

        total = float(stock.get("total_cost", 0) or 0)
        price_display = avg_buy_price if avg_buy_price > 0 else "NA"
        total_display = round(total, 2) if total > 0 else "NA"
        stock_data.append([
            stock["company_name"],
            quantity,
            price_display,
            target_price if target_set else "NA",
            total_display
        ])
        if total > 0:
            total_cost += total

    if auto_sold:
        cached_portfolio.clear()
        st.success("Auto-sell executed for: " + ", ".join(auto_sold))
        st.rerun()

    df = pd.DataFrame(
        stock_data,
        columns=["Company", "Quantity", "Price", "Target", "Total"]
    )

    df.index = df.index + 1

    st.write(f"Total Stocks: {len(df)}")
    st.write(f"Total Investment: ₹{total_cost:.2f}")

    st.dataframe(df, width='stretch')

    st.divider()

    stock_map = {}
    label_counts = {}
    for key, value in grouped_stocks.items():
        base_label = f'{value["company_name"]} ({value.get("ticker", "")})'
        count = label_counts.get(base_label, 0) + 1
        label_counts[base_label] = count
        label = base_label if count == 1 else f"{base_label} #{count}"
        stock_map[label] = (key, value)

    selected = st.selectbox(
        "Select Stock",
        list(stock_map.keys())
    )

    stock_id, stock = stock_map[selected]

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Set Target"):
            st.session_state.selected_stock = stock.get("purchase_ids", [None])[0]
            st.session_state.page = "edit_stock"
            st.rerun()

    with col2:
        if st.button("Sell"):

            success = False
            sell_price = display_prices.get(stock_id, 0)
            for purchase_id in stock.get("purchase_ids", []):
                if sell_stock(
                    purchase_id,
                    user_id,
                    sell_price,
                    mode="manual"
                ):
                    success = True

            if success:
                cached_portfolio.clear()
                st.toast("Stock sold successfully")
                st.rerun()
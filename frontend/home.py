import streamlit as st
import pandas as pd
from services.cache import cached_user, cached_portfolio
from services.stock_services import fetch_stock_data
from database.curd import sell_stock


def _display_symbol(raw_ticker):
    ticker = str(raw_ticker or "").strip().upper()
    return ticker.replace(".NS", "")


def _looks_like_ticker_name(value):
    text = str(value or "").strip().upper()
    if not text:
        return True
    if text.endswith(".NS"):
        return True
    return all(ch.isalnum() or ch in {".", "-", "&"} for ch in text) and len(text) <= 15


def _resolved_company_name(raw_name, ticker, name_map):
    ticker_key = str(ticker or "").strip().upper()
    fetched = str((name_map or {}).get(ticker_key, "")).strip()
    raw = str(raw_name or "").strip()

    if fetched and (_looks_like_ticker_name(raw) or not raw):
        return fetched
    return raw or fetched or _display_symbol(ticker_key)

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

    if st.sidebar.button("Show Portfolio Sectors"):
        st.session_state.page = "sector_user"
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

    ticker_list = [
        str(s.get("ticker", "")).strip().upper()
        for s in grouped_stocks.values()
        if str(s.get("ticker", "")).strip()
    ]
    market_meta = fetch_stock_data(ticker_list) if ticker_list else {}
    name_map = (market_meta or {}).get("name_map", {})

    stock_data = []
    display_prices = {}
    total_cost = 0
    auto_sold = []

    for stock_key, stock in grouped_stocks.items():
        ticker = str(stock.get("ticker", "")).strip().upper()
        market_price = 0

        if ticker:
            ticker_ns = ticker if ticker.endswith(".NS") else ticker + ".NS"
            market_price = round((market_meta or {}).get(ticker_ns, 0) or 0, 2)

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
                sold_name = _resolved_company_name(stock.get("company_name", ""), ticker, name_map)
                auto_sold.append(f"{sold_name} @ ₹{sell_check_price}")
                continue

        total = float(stock.get("total_cost", 0) or 0)
        price_display = avg_buy_price if avg_buy_price > 0 else None
        total_display = round(total, 2) if total > 0 else None
        display_company_name = _resolved_company_name(stock.get("company_name", ""), ticker, name_map)
        stock_data.append([
            display_company_name,
            quantity,
            price_display,
            target_price if target_set else None,
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

    # Keep columns numeric to avoid Streamlit/PyArrow conversion warnings.
    for col in ["Quantity", "Price", "Target", "Total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.index = df.index + 1

    st.write(f"Total Stocks: {len(df)}")
    st.write(f"Total Investment: ₹{total_cost:.2f}")

    st.dataframe(df, width='stretch')

    st.divider()

    stock_map = {}
    label_counts = {}
    for key, value in grouped_stocks.items():
        display_ticker = _display_symbol(value.get("ticker", ""))
        display_name = _resolved_company_name(value.get("company_name", ""), value.get("ticker", ""), name_map)
        base_label = f"{display_name} ({display_ticker})" if display_ticker else display_name
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
import streamlit as st
import pandas as pd
from database.curd import get_user_details
from services.cache import cached_transactions
from services.stock_services import fetch_stock_data


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
    key = str(ticker or "").strip().upper()
    raw = str(raw_name or "").strip()
    fetched = str((name_map or {}).get(key, "")).strip()
    if fetched and (_looks_like_ticker_name(raw) or not raw):
        return fetched
    return raw or fetched or _display_symbol(key)


@st.cache_data(ttl=10)
def load_user_details(user_id):
    return get_user_details(user_id)


def profile():

    st.title("Profile")

    # Login check
    if "user" not in st.session_state:
        st.warning("Please login first.")
        st.session_state["page"] = "login"
        st.rerun()
        return

    user_id = st.session_state["user"]

    # Navigation buttons
    col1, col2 = st.columns([2, 1])

    with col1:
        if st.button("Home"):
            st.session_state["page"] = "home"
            st.rerun()

    with col2:
        if st.button("Logout"):
            del st.session_state["user"]
            st.session_state["page"] = "landing"
            st.rerun()

    st.divider()

    # Fetch user data
    user_details = load_user_details(user_id)

    if not user_details:
        st.error("User details not found.")
        return

    st.subheader("User Details")

    col1, col2 = st.columns(2)

    with col1:
        st.write(f"**Name:** {user_details.get('name')}")
        st.write(f"**Email:** {user_details.get('email')}")

    with col2:
        st.write(f"**Phone:** {user_details.get('phone')}")

    st.divider()
    st.subheader("Transaction History")

    transactions = cached_transactions(user_id)

    if not transactions:
        st.info("No transactions found yet.")
        return

    tickers = [str(t.get("ticker", "")).strip().upper() for t in transactions if str(t.get("ticker", "")).strip()]
    market_meta = fetch_stock_data(tickers) if tickers else {}
    name_map = (market_meta or {}).get("name_map", {})

    history_df = pd.DataFrame([
        {
            "Date": t.get("timestamp", ""),
            "Type": t.get("action", ""),
            "Mode": t.get("mode", ""),
            "Company": _resolved_company_name(t.get("company_name", ""), t.get("ticker", ""), name_map),
            "Ticker": _display_symbol(t.get("ticker", "")),
            "Quantity": t.get("quantity", 0),
            "Price": round(float(t.get("price_per_stock", 0) or 0), 2),
            "Total": round(float(t.get("total_value", 0) or 0), 2),
        }
        for t in transactions
    ])

    st.dataframe(history_df, width='stretch')
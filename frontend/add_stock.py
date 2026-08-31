"""Add a stock by ticker. Name and sector are fetched, never typed."""

import streamlit as st

from database.manager_operation import add_stock_to_db
from frontend.manger_home import require_manager
from services.cache import cached_stocks
from services.stock_services import get_profile, get_price, display_symbol


def add_stock():
    if not require_manager():
        return

    st.title("Add Stock")
    st.caption("Enter an NSE symbol. Everything else is resolved from market data.")

    symbol = st.text_input("NSE Symbol", placeholder="TCS").strip().upper()
    if not symbol:
        return

    profile = get_profile(symbol)
    if not profile["resolved"]:
        st.error(f"'{symbol}' did not resolve on NSE. Check the symbol.")
        return

    price = get_price(symbol)
    c1, c2 = st.columns(2)
    c1.text_input("Name", value=profile["name"], disabled=True)
    c2.text_input("Sector", value=profile["sector"], disabled=True)
    st.metric("Live Price", f"₹{price:,.2f}" if price else "unavailable")

    existing = {str(s.get("ticker", "")).upper()
                for s in (cached_stocks() or {}).values()}
    if profile["ticker"] in existing or display_symbol(profile["ticker"]) in existing:
        st.info("Already in the catalog.")
        return

    if st.button("Add to catalog", type="primary"):
        # Price is deliberately not stored -- it is stale the moment it is written.
        if add_stock_to_db(profile["name"], profile["ticker"], 0.0, profile["sector"]):
            cached_stocks.clear()
            st.success(f"Added {profile['name']}")
            st.session_state["page"] = "show_stocks"
            st.rerun()
        st.error("Failed to add stock.")


if __name__ == "__main__":
    add_stock()

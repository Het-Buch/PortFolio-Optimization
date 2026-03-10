import streamlit as st
from services.cache import cached_stocks, cached_portfolio
from database.curd import add_purchase_to_db
from services.stock_services import fetch_stock_data


def _clean_ticker(ticker):
    return str(ticker or "").strip().upper()

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

    tickers = [_clean_ticker(v.get("ticker", "")) for v in active_stocks.values()]
    market_meta = fetch_stock_data(tickers) if tickers else {}
    name_map = (market_meta or {}).get("name_map", {})

    display_to_id = {}
    for sid, stock in active_stocks.items():
        ticker = _clean_ticker(stock.get("ticker", ""))
        fallback_name = str(stock.get("name", "") or "").strip()
        resolved_name = str(name_map.get(ticker, fallback_name)).strip() or fallback_name or ticker.replace(".NS", "")
        display_to_id[f"{resolved_name} ({ticker.replace('.NS', '')})"] = sid

    company_names = sorted(display_to_id.keys())

    st.subheader("Purchase Stocks")

    selected_label = st.selectbox("Select Company", company_names, index=None, placeholder="Choose a stock")

    if not selected_label:
        st.info("Select a stock to view price and continue.")
        return

    quantity = st.number_input(
        "Enter quantity",
        min_value=1,
        step=1
    )

    selected_stock_id = display_to_id.get(selected_label)
    selected_stock = active_stocks.get(selected_stock_id)

    if not selected_stock:
        st.warning("Selected stock is unavailable. Please choose another stock.")
        return

    ticker = str(selected_stock["ticker"]).strip().upper()
    stock_id = selected_stock["stock_id"]
    company_name = str(name_map.get(ticker, selected_stock.get("name", ""))).strip() or ticker.replace(".NS", "")
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
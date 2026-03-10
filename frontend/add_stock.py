import streamlit as st
from database.manager_operation import add_stock_to_db
from services.stock_services import fetch_stock_data

def add_stock():

    st.title("Add New Stock")

    if st.button("Back to Home"):
        st.session_state["page"] = "manager_home"
        st.rerun()

    # Persist fetched data
    if "stock_name" not in st.session_state:
        st.session_state.stock_name = ""

    if "stock_price" not in st.session_state:
        st.session_state.stock_price = 0.0

    if "valid_stock" not in st.session_state:
        st.session_state.valid_stock = False

    if "stock_sector" not in st.session_state:
        st.session_state.stock_sector = "Unknown"


    stock_ticker = st.text_input("Stock Symbol").strip().upper()

    if st.button("Fetch Stock Info"):
        if not stock_ticker:
            st.warning("Enter a stock symbol first")
        if len(stock_ticker) < 3:
            st.warning("Enter a valid stock ticker")
        else:
            data = fetch_stock_data(stock_ticker)
            if data and "name" in data:
                name = data.get("name", stock_ticker.upper())
                price = round(float(data.get("price", 0) or 0), 2)

                st.session_state.stock_name = name
                st.session_state.stock_price = price
                st.session_state.stock_sector = str(data.get("sector", "Unknown") or "Unknown").strip() or "Unknown"
                st.session_state.valid_stock = True

                if price > 0:
                    st.success(f"{name} | Live Price: ₹{price}")
                else:
                    st.warning("Live price unavailable right now. You can still add this stock and price will load later.")

            else:
                st.session_state.stock_name = stock_ticker
                st.session_state.stock_price = 0.0
                st.session_state.stock_sector = "Unknown"
                st.session_state.valid_stock = True
                st.warning("Live price unavailable right now. You can still add this stock and price will load later.")

    # Locked fields
    st.text_input(
        "Stock Name",
        value=st.session_state.stock_name,
        disabled=True
    )

    sector = st.text_input(
        "Sector",
        value=st.session_state.stock_sector,
        placeholder="e.g., IT, Banking, Pharma"
    ).strip() or "Unknown"

    st.number_input(
        "Stock Price",
        value=float(st.session_state.stock_price),
        format="%.2f",
        disabled=True
    )


    col1, col2 = st.columns(2)

    with col1:

        if st.button("Add Stock", disabled=not st.session_state.valid_stock):

            if add_stock_to_db(
                st.session_state.stock_name,
                stock_ticker,
                st.session_state.stock_price,
                sector
            ):
                st.toast("Stock added successfully")
                # Clear cached values
                st.session_state.stock_name = ""
                st.session_state.stock_price = 0.0
                st.session_state.stock_sector = "Unknown"
                st.session_state.valid_stock = False
                st.session_state["page"] = "manager_home"
                st.rerun()
            else:
                st.error("Failed to add stock")

    with col2:

        if st.button("Back to Home", key="add_stock_back_bottom"):

            st.session_state["page"] = "manager_home"
            st.rerun()


if __name__ == "__main__":
    add_stock()
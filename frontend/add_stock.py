import streamlit as st
from database.manager_operation import add_stock_to_db
from services.stock_services import fetch_stock_data

def add_stock():

    st.title("Add New Stock")

    # Persist fetched data
    if "stock_name" not in st.session_state:
        st.session_state.stock_name = ""

    if "stock_price" not in st.session_state:
        st.session_state.stock_price = 0.0

    if "valid_stock" not in st.session_state:
        st.session_state.valid_stock = False


    stock_ticker = st.text_input("Stock Symbol").upper()

    if st.button("Fetch Stock Info"):
        if not stock_ticker:
            st.warning("Enter a stock symbol first")
        if len(stock_ticker) < 3:
            st.warning("Enter a valid stock ticker")
        else:
            data = fetch_stock_data(stock_ticker)
            if data and "price" in data:
                name = data.get("name", stock_ticker.upper())
                price = round(float(data["price"]), 2)

                st.session_state.stock_name = name
                st.session_state.stock_price = price
                st.session_state.valid_stock = True

                st.success(f"{name} | Live Price: ₹{price}")

            else:
                st.session_state.valid_stock = False
                st.warning("Unable to fetch stock. Yahoo may be rate limiting.")

    # Locked fields
    st.text_input(
        "Stock Name",
        value=st.session_state.stock_name,
        disabled=True
    )

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
                stock_ticker
            ):
                st.toast("Stock added successfully")
                # Clear cached values
                st.session_state.stock_name = ""
                st.session_state.stock_price = 0.0
                st.session_state.valid_stock = False
                st.session_state["page"] = "manager_home"
                st.rerun()
            else:
                st.error("Failed to add stock")

    with col2:

        if st.button("Go to Home Page"):

            st.session_state["page"] = "manager_home"
            st.rerun()


if __name__ == "__main__":
    add_stock()
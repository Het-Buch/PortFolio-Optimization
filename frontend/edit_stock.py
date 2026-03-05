import streamlit as st
from database.curd import get_stock_data, set_target_price
from services.cache import cached_portfolio


@st.cache_data(ttl=10)
def load_stock(stock_id):
    return get_stock_data(stock_id)


def edit_stock():

    st.title("Set Target Price")

    if st.button("Back to Home"):
        st.session_state["page"] = "home"
        st.rerun()

    purchased_id = st.session_state.get("selected_stock")

    if not purchased_id:
        st.error("No stock selected.")
        st.session_state["page"] = "home"
        st.rerun()
        return

    stock_data = load_stock(purchased_id)

    if not stock_data:
        st.error("Stock not found.")
        return

    stock_name = st.text_input(
        "Stock Name",
        value=stock_data.get("company_name", ""),
        disabled=True
    )

    stock_ticker = st.text_input(
        "Stock Ticker",
        value=stock_data.get("ticker", ""),
        disabled=True
    )

    stock_price = st.number_input(
        "Bought Price",
        value=round(float(stock_data.get("price_per_stock", 0.0)), 2),
        step=0.01,
        format="%.2f",
        disabled=True
    )

    quantity = st.number_input(
        "Number of Stocks",
        value=int(stock_data.get("quantity", 1)),
        min_value=1,
        step=1,
        disabled=True
    )

    target_default = round(float(stock_data.get("target_price", 0.0) or 0.0), 2)

    target_price = st.number_input(
        "Target Price (Auto Sell)",
        value=target_default,
        min_value=0.0,
        step=0.01,
        format="%.2f"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Set Target"):

            if target_price <= 0:
                st.error("Target price must be greater than 0.")
                return

            success = set_target_price(
                purchased_id,
                target_price,
                st.session_state["user"]
            )

            if success:
                cached_portfolio.clear()
                st.toast("Target price set successfully")
                st.session_state["page"] = "home"
                st.rerun()

            else:
                st.error("Update failed.")

    with col2:
        if st.button("Cancel"):
            st.session_state["page"] = "home"
            st.rerun()


if __name__ == "__main__":
    edit_stock()
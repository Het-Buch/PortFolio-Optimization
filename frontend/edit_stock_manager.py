import streamlit as st
from database.manager_operation import get_stock_data, update_stock_data


@st.cache_data(ttl=10)
def load_stock(stock_id):
    """Cache stock fetch to reduce DB calls"""
    return get_stock_data(stock_id)


def edit_stock_manager():

    # Login check
    if "user" not in st.session_state:
        st.warning("You are not logged in. Please login first.")
        st.session_state["page"] = "landing"
        st.rerun()
        return

    st.title("Edit Stock")

    if st.button("Back to Home"):
        st.session_state["page"] = "manager_home"
        st.rerun()

    stock_id = st.session_state.get("selected_stock")

    if not stock_id:
        st.error("No stock selected.")
        st.session_state["page"] = "manager_home"
        st.rerun()
        return

    stock_data = load_stock(stock_id)

    if not stock_data:
        st.error("Stock not found.")
        st.session_state["page"] = "show_stocks"
        st.rerun()
        return

    # Input fields
    stock_name = st.text_input(
        "Stock Name",
        value=stock_data.get("name", "")
    )

    stock_ticker = st.text_input(
        "Stock Ticker",
        value=stock_data.get("ticker", "")
    ).upper()

    sector = st.text_input(
        "Sector",
        value=str(stock_data.get("sector", "Unknown") or "Unknown").strip() or "Unknown"
    ).strip() or "Unknown"

    stock_price = st.number_input(
        "Stock Price",
        value=round(float(stock_data.get("price", 0.0)), 2),
        step=0.01,
        format="%.2f"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Update Stock"):

            success = update_stock_data(
                stock_id,
                stock_name,
                stock_ticker,
                stock_price,
                st.session_state["user"],
                sector,
            )

            if success:
                st.toast("Stock updated successfully")
                st.session_state["page"] = "show_stocks"
                st.rerun()
            else:
                st.error("Failed to update stock.")

    with col2:
        if st.button("Cancel"):
            st.session_state["page"] = "show_stocks"
            st.rerun()


if __name__ == "__main__":
    edit_stock_manager()
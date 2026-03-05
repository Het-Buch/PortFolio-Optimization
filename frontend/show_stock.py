import streamlit as st
import pandas as pd

from services.cache import cached_stocks
from database.manager_operation import delete_stock_from_db

def show_stocks():

    st.title("Stocks List")

    stocks = cached_stocks()

    if not stocks:
        st.warning("No stocks available.")
        return

    # Convert Firebase data to DataFrame
    stock_list = [
        {
            "ID": stock_id,
            "Name": stock.get("name"),
            "Ticker": stock.get("ticker"),
        }
        for stock_id, stock in stocks.items()
        if not stock.get("is_deleted", False)
    ]

    if not stock_list:
        st.info("All stocks are deleted.")
        return

    df = pd.DataFrame(stock_list)
    df.index = df.index + 1

    st.dataframe(
        df.drop(columns=["ID"]),
        width='stretch',
    )

    st.divider()

    st.subheader("Manage Stock")

    stock_map = {
        f'{row["Name"]} ({row["Ticker"]})': row["ID"]
        for _, row in df.iterrows()
    }

    selected_display = st.selectbox(
        "Select Stock",
        list(stock_map.keys())
    )
    selected_stock = stock_map[selected_display]

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Edit Stock"):

            st.session_state["selected_stock"] = selected_stock
            st.session_state["page"] = "edit_stock_manager"

            st.rerun()

    with col2:
        if st.button("Delete Stock"):

            success = delete_stock_from_db(selected_stock)

            if success:
                # clear cache so table refreshes immediately
                cached_stocks.clear()
                st.toast("Stock deleted successfully")
                st.rerun()

            else:
                st.error("Failed to delete stock.")

    st.divider()

    if st.button("Back to Dashboard"):
        st.session_state["page"] = "manager_home"
        st.rerun()


if __name__ == "__main__":
    show_stocks()
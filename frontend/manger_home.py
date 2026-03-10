import streamlit as st
import pandas as pd

from services.cache import cached_user_growth, cached_purchase_growth

def manager_home():

    # Safety check
    if "user" not in st.session_state or st.session_state["user"] != "manager":
        st.session_state["page"] = "landing"
        st.rerun()
        return

    st.title("Manager Dashboard")

    # Sidebar navigation
    st.sidebar.title("Navigation")

    if st.sidebar.button("Home"):
        st.session_state["page"] = "manager_home"
        st.rerun()

    if st.sidebar.button("Add New Stock"):
        st.session_state["page"] = "add_stock"
        st.rerun()

    if st.sidebar.button("Show Stocks"):
        st.session_state["page"] = "show_stocks"
        st.rerun()

    if st.sidebar.button("Show Users"):
        st.session_state["page"] = "show_users"
        st.rerun()

    if st.sidebar.button("Show Stock Sectors"):
        st.session_state["page"] = "sector_manager"
        st.rerun()

    if st.sidebar.button("Logout"):
        del st.session_state["user"]
        st.session_state["page"] = "landing"
        st.rerun()

    st.divider()

    # -------------------------
    # User growth chart
    # -------------------------
    user_data = cached_user_growth()

    st.subheader("📈 User Growth Over Time")

    if user_data:

        df = pd.DataFrame(user_data)
        df["first_login"] = pd.to_datetime(df["first_login"])

        login_counts = df.groupby(df["first_login"].dt.date).size()

        st.line_chart(login_counts)

    else:
        st.info("No user data available.")

    st.divider()

    # -------------------------
    # Purchases chart
    # -------------------------
    purchase_data = cached_purchase_growth()

    st.subheader("📊 Purchases by Company")

    if purchase_data:

        df = pd.DataFrame(purchase_data)

        purchase_summary = df.groupby("company_name")["quantity"].sum()

        st.bar_chart(purchase_summary)

    else:
        st.info("No purchase data available.")


if __name__ == "__main__":
    manager_home()
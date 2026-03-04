import streamlit as st
from database.curd import get_user_details


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
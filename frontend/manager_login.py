import streamlit as st
from database.manager_login import authenticate_manager


def manager_login():

    st.title("Manager Login")

    # Input fields
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login"):

            # Basic validation
            if not email or not password:
                st.warning("Please enter both email and password.")
                return

            user_id = authenticate_manager(email, password)

            if user_id:

                st.session_state["user"] = user_id
                st.session_state["page"] = "manager_home"

                st.success("Login Successful")
                st.rerun()

            else:
                st.error("Invalid credentials")

    with col2:
        if st.button("Back"):

            st.session_state["page"] = "landing"
            st.rerun()


if __name__ == "__main__":
    manager_login()
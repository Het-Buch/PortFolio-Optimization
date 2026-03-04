import streamlit as st
from database.login_user import authenticate_user


def login():

    st.title("Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):

        user_id = authenticate_user(email, password)

        if user_id:

            st.session_state["user"] = user_id
            st.session_state["page"] = "home"

            st.success("Login Successful")
            st.rerun()

        else:
            st.error("Invalid credentials")
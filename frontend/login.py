"""Login: email/password or Google. Both resolve to the same user_id."""

import streamlit as st

from database.auth import is_manager, sign_in_with_google
from database.login_user import authenticate_user
from frontend.session_ui import start


def _google_configured():
    """st.login raises if no [auth] block exists; check before offering it."""
    try:
        return "auth" in st.secrets
    except Exception:
        return False


def _enter(user_id, manager=False):
    start(user_id or "manager", is_manager=manager)
    st.session_state["page"] = "manager_home" if manager else "home"
    st.rerun()


def login():
    st.title("Login")

    # Returning from the Google redirect — resolve the identity and continue.
    if _google_configured() and getattr(st.user, "is_logged_in", False):
        email = st.user.email
        if is_manager(email):
            _enter(None, manager=True)
        user_id = sign_in_with_google(email, getattr(st.user, "name", ""))
        if user_id:
            _enter(user_id)
        st.error("This account is blocked. Contact the manager.")
        st.logout()
        return

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login", type="primary"):
        if not email or not password:
            st.warning("Enter both email and password.")
        else:
            user_id = authenticate_user(email, password)
            if user_id:
                _enter(user_id)
            st.error("Invalid credentials")

    if _google_configured():
        st.divider()
        if st.button("Continue with Google"):
            st.login("google")

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Register"):
            st.session_state["page"] = "register"
            st.rerun()
    with col2:
        if st.button("Back"):
            st.session_state["page"] = "landing"
            st.rerun()

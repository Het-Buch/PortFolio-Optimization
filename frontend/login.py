"""User login only. Email/password or Google, both resolve to a user_id.
Managers have a separate route (frontend/login_manager.py) -- this page must
never grant manager access, even if a manager's Google account signs in here."""

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


def _enter(user_id):
    start(user_id)
    st.session_state["page"] = "home"
    # Pay the cold-cache cost here, behind the login spinner, instead of
    # mid-render on the first page the user lands on.
    from services.cache import warm
    with st.spinner("Loading your portfolio..."):
        warm(user_id)
    st.rerun()


def login():
    # Returning from the Google redirect — resolve the identity and continue.
    if _google_configured() and getattr(st.user, "is_logged_in", False):
        email = st.user.email
        if is_manager(email):
            st.error("This is a manager account. Use the manager portal to log in.")
            st.logout()
            return
        user_id = sign_in_with_google(email, getattr(st.user, "name", ""))
        if user_id:
            _enter(user_id)
        st.error("This account is blocked. Contact the manager.")
        st.logout()
        return

    from frontend.landing import _hero
    _hero()

    # Constrain the form to a card width -- full-browser-width inputs is what
    # reads as an empty page, not the field count.
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.title("Welcome back")
        st.caption("Log in to see your portfolio and rebalance it.")

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Login", type="primary", width="stretch"):
            if not email or not password:
                st.warning("Enter both email and password.")
            else:
                user_id = authenticate_user(email, password)
                if user_id:
                    _enter(user_id)
                st.error("Invalid credentials")

        if _google_configured():
            if st.button("Continue with Google", width="stretch"):
                st.login("google")

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Register", width="stretch"):
                st.session_state["page"] = "register"
                st.rerun()
        with col2:
            if st.button("Back", width="stretch"):
                st.session_state["page"] = "landing"
                st.rerun()

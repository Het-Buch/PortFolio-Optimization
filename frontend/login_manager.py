"""Manager portal login. Separate route from frontend/login.py on purpose --
manager access is an email allowlist (database.auth.is_manager), never a path
a regular user can wander into."""

import streamlit as st

from database.auth import authenticate_manager, is_manager
from frontend.session_ui import start


def _google_configured():
    try:
        return "auth" in st.secrets
    except Exception:
        return False


def _enter():
    start("manager", is_manager=True)
    st.session_state["page"] = "manager_home"
    st.rerun()


def login_manager():
    if _google_configured() and getattr(st.user, "is_logged_in", False):
        email = st.user.email
        if is_manager(email):
            _enter()
        st.error("This Google account is not on the manager allowlist.")
        st.logout()
        return

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown("## :material/shield_person: Manager portal")
        st.caption("Restricted access. Sign in with an allowlisted manager account.")

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Sign in", type="primary", width="stretch",
                     icon=":material/shield_person:"):
            if not email or not password:
                st.warning("Enter both email and password.")
            elif authenticate_manager(email, password):
                _enter()
            else:
                st.error("Invalid manager credentials.")

        if _google_configured():
            if st.button("Continue with Google", width="stretch"):
                st.login("google")

        st.divider()
        if st.button("Back", width="stretch", icon=":material/arrow_back:"):
            st.session_state["page"] = "landing"
            st.rerun()

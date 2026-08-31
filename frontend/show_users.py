import streamlit as st

from frontend.manger_home import require_manager
import pandas as pd

from services.cache import cached_users

def show_users():

    st.title("User List")

    # Safe session check
    if not require_manager():
        return

    users = cached_users()

    if not users:
        st.warning("No users found.")
        if st.button("Back to Home"):
            st.session_state["page"] = "manager_home"
            st.rerun()
        return

    user_data = [
        {
            "User ID": user.get("personal", {}).get("user_id"),
            "Email": user.get("personal", {}).get("email"),
            "Name": user.get("personal", {}).get("name"),
            "Phone": user.get("personal", {}).get("phone"),
            "Last Login": user.get("login", {}).get("last_login_date"),
            "Blocked": user.get("personal", {}).get("blocked"),
        }
        for user in users.values()
    ]

    df = pd.DataFrame(user_data)
    df.index = df.index + 1

    st.dataframe(
        df,
        width='stretch'
    )

    st.divider()

    if st.button("Back to Home"):
        st.session_state["page"] = "manager_home"
        st.rerun()


if __name__ == "__main__":
    show_users()
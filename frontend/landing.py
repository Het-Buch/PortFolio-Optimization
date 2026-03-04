import streamlit as st


def landing():

    if "page" not in st.session_state:
        st.session_state.page = "landing"

    page = st.session_state.page

    if page == "landing":

        st.title("Portfolio Management System")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Register"):
                st.session_state.page = "register"
                st.rerun()

        with col2:
            if st.button("Login"):
                st.session_state.page = "login"
                st.rerun()

        st.divider()

        if st.button("Manager"):
            st.session_state.page = "manager_login"
            st.session_state["user"] = "manager"
            st.rerun()

    elif page == "home":
        from frontend.home import home
        home()

    elif page == "register":
        from frontend.register import register
        register()

    elif page == "login":
        from frontend.login import login
        login()

    elif page == "profile":
        from frontend.profile import profile
        profile()

    elif page == "buy":
        from frontend.buy import buy
        buy()

    elif page == "optimize":
        from frontend.optimize import optimize
        optimize()

    elif page == "manager_home":
        from frontend.manger_home import manager_home
        manager_home()

    elif page == "manager_login":
        from frontend.manager_login import manager_login
        manager_login()

    elif page == "add_stock":
        from frontend.add_stock import add_stock
        add_stock()

    elif page == "show_stocks":
        from frontend.show_stock import show_stocks
        show_stocks()

    elif page == "edit_stock":
        from frontend.edit_stock import edit_stock
        edit_stock()

    elif page == "edit_stock_manager":
        from frontend.edit_stock_manager import edit_stock_manager
        edit_stock_manager()
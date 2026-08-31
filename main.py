"""Entry point. Fails fast and loudly if configuration is missing."""

import streamlit as st

st.set_page_config(page_title="Portfolio Management System",
                   page_icon="📈", layout="wide")


def main():
    try:
        from database.connection import initialize_firebase
        initialize_firebase()
    except Exception as e:
        st.error(f"Configuration error: {e}")
        st.stop()

    from frontend.landing import landing
    landing()


if __name__ == "__main__":
    main()

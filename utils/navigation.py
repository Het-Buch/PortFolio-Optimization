import streamlit as st

def go(page):
    st.session_state["page"] = page
    st.rerun()
import streamlit as st

from database.curd import get_purchased_stocks, get_user_details, get_user_transactions
from database.manager_operation import get_all_stocks_from_db, get_users
from database.manager_operation import get_users_first_login, get_user_purchases_over_time


@st.cache_data(ttl=30, show_spinner=False)
def cached_portfolio(user_id):
    return get_purchased_stocks(user_id)


@st.cache_data(ttl=30, show_spinner=False)
def cached_user(user_id):
    return get_user_details(user_id)


@st.cache_data(ttl=30, show_spinner=False)
def cached_stocks():
    return get_all_stocks_from_db()


@st.cache_data(ttl=30, show_spinner=False)
def cached_users():
    return get_users()


@st.cache_data(ttl=30, show_spinner=False)
def cached_user_growth():
    return get_users_first_login()


@st.cache_data(ttl=30, show_spinner=False)
def cached_purchase_growth():
    return get_user_purchases_over_time()


@st.cache_data(ttl=30, show_spinner=False)
def cached_transactions(user_id):
    return get_user_transactions(user_id)

from ml.train import train_models


@st.cache_data(ttl=3600, show_spinner=False)
def cached_prediction(ticker, company):
    return train_models(ticker, company)
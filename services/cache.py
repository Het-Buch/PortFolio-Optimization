"""Cached DB reads. Heavy imports stay inside functions to keep startup fast."""

import streamlit as st

TTL = 60


@st.cache_data(ttl=TTL, show_spinner=False)
def cached_portfolio(user_id):
    from database.curd import get_purchased_stocks
    return get_purchased_stocks(user_id)


@st.cache_data(ttl=TTL, show_spinner=False)
def cached_user(user_id):
    from database.curd import get_user_details
    return get_user_details(user_id)


@st.cache_data(ttl=TTL, show_spinner=False)
def cached_transactions(user_id):
    from database.curd import get_user_transactions
    return get_user_transactions(user_id)


@st.cache_data(ttl=TTL, show_spinner=False)
def cached_stocks():
    from database.manager_operation import get_all_stocks_from_db
    return get_all_stocks_from_db()


@st.cache_data(ttl=TTL, show_spinner=False)
def cached_users():
    from database.manager_operation import get_users
    return get_users()


@st.cache_data(ttl=TTL, show_spinner=False)
def cached_user_growth():
    from database.manager_operation import get_users_first_login
    return get_users_first_login()


@st.cache_data(ttl=TTL, show_spinner=False)
def cached_purchase_growth():
    from database.manager_operation import get_user_purchases_over_time
    return get_user_purchases_over_time()


def clear_all():
    """Call after any write that changes what these return."""
    for fn in (cached_portfolio, cached_user, cached_transactions, cached_stocks,
               cached_users, cached_user_growth, cached_purchase_growth):
        fn.clear()

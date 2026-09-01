"""Cached DB reads. Heavy imports stay inside functions to keep startup fast."""

import streamlit as st

# A user's own data changes only when they act, and every such write already
# calls .clear() -- so the TTL is a safety net, not the correctness mechanism.
# At 300s, navigating after a short pause re-paid a full Firebase round-trip
# mid-render. 1800s matches the session length, so a whole session navigates
# from cache. Prices are separate and stay at 300s in stock_services, because
# market data genuinely does go stale.
OWN_TTL = 1800

# Manager views are not cleared by another user's registration or purchase, so
# these stay short or a manager would see a stale roster for half an hour.
TTL = 300


@st.cache_data(ttl=OWN_TTL, show_spinner=False)
def cached_portfolio(user_id):
    from database.curd import get_purchased_stocks
    return get_purchased_stocks(user_id)


@st.cache_data(ttl=OWN_TTL, show_spinner=False)
def cached_user(user_id):
    from database.curd import get_user_details
    return get_user_details(user_id)


@st.cache_data(ttl=OWN_TTL, show_spinner=False)
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


def warm(user_id):
    """Prefetch everything the first page needs, in parallel, at login time.

    Cold, these cost ~3.1s sequentially (0.33 user + 0.68 portfolio + 2.11
    prices) and they were being paid mid-render on the first navigation, so the
    layout painted and then froze. Paying them here puts the wait behind the
    login spinner, where it reads as intentional, and every page afterwards
    renders from cache. Never raises: a failed prefetch just means the page
    fetches it the old way.
    """
    from concurrent.futures import ThreadPoolExecutor

    def _prices():
        from services.stock_services import get_prices, normalize_ticker
        rows = cached_portfolio(user_id) or {}
        tickers = sorted({normalize_ticker(r.get("ticker"))
                          for r in rows.values()
                          if r and not r.get("sold") and r.get("ticker")} - {""})
        return get_prices(tickers) if tickers else {}

    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs = [pool.submit(cached_user, user_id),
                    pool.submit(cached_portfolio, user_id),
                    pool.submit(cached_stocks)]
            for j in jobs:
                j.result()
        _prices()
    except Exception:
        pass

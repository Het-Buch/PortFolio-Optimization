"""Manager dashboard: KPIs, growth, holdings, and recent activity."""

import pandas as pd
import streamlit as st

from services.cache import (cached_purchase_growth, cached_stocks,
                            cached_user_growth, cached_users)


def require_manager():
    """Shared guard. Every manager page calls this."""
    if st.session_state.get("user") != "manager":
        st.session_state["page"] = "landing"
        st.rerun()
        return False
    return True


def manager_home():
    if not require_manager():
        return

    st.title("Manager Dashboard")

    users = cached_users() or {}
    stocks = cached_stocks() or {}
    purchases = cached_purchase_growth() or []

    blocked = sum(1 for u in users.values()
                  if (u or {}).get("personal", {}).get("blocked"))
    units = sum(int(p.get("quantity", 0) or 0) for p in purchases)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Users", len(users), delta=f"-{blocked} blocked" if blocked else None)
    c2.metric("Listed Stocks", len(stocks))
    c3.metric("Purchases", len(purchases))
    c4.metric("Units Held", f"{units:,}")

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("User Growth")
        growth = cached_user_growth() or []
        dates = pd.to_datetime(
            [g.get("first_login") for g in growth if g.get("first_login")],
            errors="coerce").dropna()
        if len(dates):
            series = pd.Series(1, index=dates).resample("D").sum().cumsum()
            st.area_chart(series, height=240)
        else:
            st.info("No signup history yet.")

    with right:
        st.subheader("Top Holdings")
        if purchases:
            df = pd.DataFrame(purchases)
            df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
            top = df.groupby("company_name")["quantity"].sum().nlargest(8)
            st.bar_chart(top, height=240)
        else:
            st.info("No purchases yet.")

    st.divider()
    st.subheader("Recent Purchases")
    if purchases:
        df = pd.DataFrame(purchases).rename(columns={
            "company_name": "Company", "purchase_date": "Date", "quantity": "Qty"})
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values("Date", ascending=False, na_position="last").head(10)
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("Nothing to show.")


if __name__ == "__main__":
    manager_home()

"""Manager dashboard: KPIs, growth, holdings, and recent activity."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from frontend import ui
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
    st.caption("Platform activity across every user and listed stock.")

    users = cached_users() or {}
    stocks = cached_stocks() or {}
    purchases = cached_purchase_growth() or []

    blocked = sum(1 for u in users.values()
                  if (u or {}).get("personal", {}).get("blocked"))
    units = sum(int(p.get("quantity", 0) or 0) for p in purchases)

    ui.label("At a glance")
    cols = st.columns(4)
    tiles = [("Users", len(users), f"-{blocked} blocked" if blocked else None),
             ("Listed Stocks", len(stocks), None),
             ("Purchases", len(purchases), None),
             ("Units Held", f"{units:,}", None)]
    for col, (lbl, val, delta) in zip(cols, tiles):
        with col:
            with st.container(border=True):
                st.metric(lbl, val, delta)

    left, right = st.columns(2)

    with left:
        st.markdown("##### :material/trending_up: User growth")
        with st.container(border=True):
            growth = cached_user_growth() or []
            dates = pd.to_datetime(
                [g.get("first_login") for g in growth if g.get("first_login")],
                errors="coerce").dropna()
            if len(dates):
                series = pd.Series(1, index=dates).resample("D").sum().cumsum()
                fig = go.Figure(go.Scatter(
                    x=series.index, y=series.values, mode="lines",
                    line=dict(color=ui.BLUE, width=2.5),
                    fill="tozeroy", fillcolor=ui.rgba(ui.BLUE, 0.18)))
                st.plotly_chart(ui.style_chart(fig, height=250), width="stretch")
            else:
                st.caption("No signup history yet.")

    with right:
        st.markdown("##### :material/inventory: Top holdings")
        with st.container(border=True):
            if purchases:
                df = pd.DataFrame(purchases)
                df["quantity"] = pd.to_numeric(df["quantity"],
                                               errors="coerce").fillna(0)
                top = df.groupby("company_name")["quantity"].sum().nlargest(8)
                fig = go.Figure(go.Bar(
                    y=list(top.index), x=list(top.values), orientation="h",
                    marker_color=ui.GREEN,
                    text=[f"{v:,.0f}" for v in top.values],
                    textposition="outside", cliponaxis=False,
                    hovertemplate="<b>%{y}</b><br>%{x:,.0f} units held<extra></extra>"))
                st.plotly_chart(ui.style_chart(fig, height=250, title_x="units"),
                               width="stretch")
            else:
                st.caption("No purchases yet.")

    ui.label("Recent purchases")
    if purchases:
        df = pd.DataFrame(purchases)
        df["purchase_date"] = pd.to_datetime(df.get("purchase_date"),
                                             errors="coerce")
        df = df.sort_values("purchase_date", ascending=False,
                            na_position="last").head(10)
        for _, row in df.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1.5, 2])
                c1.markdown(f"**{row.get('company_name', '—')}**")
                c2.html(ui.pill(f"{int(row.get('quantity', 0) or 0)} units", "info"))
                date = row.get("purchase_date")
                c3.caption("—" if pd.isna(date) else date.strftime("%d %b %Y, %H:%M"))
    else:
        ui.empty("receipt_long", "No purchases yet",
                "Activity will appear here once users start buying.")


if __name__ == "__main__":
    manager_home()

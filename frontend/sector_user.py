import streamlit as st
import pandas as pd
import plotly.express as px

from services.cache import cached_portfolio


PIE_COLORS = [
    "#1F7A8C", "#E27D60", "#85DCB0", "#E8A87C", "#C38D9E",
    "#41B3A3", "#F4A261", "#2A9D8F", "#264653", "#D62828",
]


def sector_user():
    if "user" not in st.session_state:
        st.warning("Please login first.")
        st.session_state["page"] = "login"
        st.rerun()
        return

    if st.session_state.get("user") == "manager":
        st.warning("Manager can view only added-stock sector split from manager dashboard.")
        st.session_state["page"] = "manager_home"
        st.rerun()
        return

    st.title("Portfolio by Sector")

    if st.button("Back to Home"):
        st.session_state["page"] = "home"
        st.rerun()

    user_id = st.session_state["user"]
    holdings = cached_portfolio(user_id) or {}

    active_holdings = [h for h in holdings.values() if not h.get("sold", False)]
    if not active_holdings:
        st.info("No active holdings available.")
        return

    rows = []
    for h in active_holdings:
        sector = str(h.get("sector", "Unknown") or "Unknown").strip() or "Unknown"
        quantity = int(h.get("quantity", 0) or 0)
        total_cost = float(h.get("total_cost", 0) or 0)
        if total_cost <= 0:
            price = float(h.get("price_per_stock", 0) or 0)
            total_cost = quantity * price

        rows.append({
            "Sector": sector,
            "Value": float(total_cost),
            "Holdings": 1,
        })

    df = pd.DataFrame(rows)
    summary = df.groupby("Sector", as_index=False).agg(
        Holdings=("Holdings", "sum"),
        Value=("Value", "sum"),
    )
    summary = summary.sort_values("Value", ascending=False)

    total_value = float(summary["Value"].sum() or 0)
    summary["Share %"] = summary["Value"].apply(lambda v: round((v / total_value * 100.0), 2) if total_value > 0 else 0.0)

    fig = px.pie(
        summary,
        names="Sector",
        values="Value",
        hole=0.45,
        color="Sector",
        color_discrete_sequence=PIE_COLORS,
    )

    fig.update_traces(
        textinfo="label",
        textposition="inside",
        insidetextorientation="radial",
        customdata=summary[["Share %"]],
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Invested: Rs %{value:,.2f}<br>"
            "Share: %{customdata[0]:.2f}%<extra></extra>"
        ),
        marker=dict(line=dict(color="#FFFFFF", width=2)),
    )

    fig.update_layout(
        showlegend=True,
        margin=dict(l=10, r=10, t=10, b=10),
        legend_title_text="Sector",
        annotations=[
            dict(
                text=f"Total<br>Rs {total_value:,.0f}",
                x=0.5,
                y=0.5,
                font=dict(size=16),
                showarrow=False,
            )
        ],
    )

    st.plotly_chart(fig, width='stretch')


if __name__ == "__main__":
    sector_user()

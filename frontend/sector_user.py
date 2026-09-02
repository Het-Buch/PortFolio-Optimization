import streamlit as st
import pandas as pd
import plotly.express as px

from frontend import ui
from services.cache import cached_portfolio


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
    st.caption("Where your money actually sits, grouped by industry.")

    user_id = st.session_state["user"]
    holdings = cached_portfolio(user_id) or {}

    active_holdings = [h for h in holdings.values() if not h.get("sold", False)]
    if not active_holdings:
        ui.empty("donut_large", "Nothing to break down",
                "Buy a stock and your sector split appears here.",
                "Browse stocks", "buy")
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
        color_discrete_sequence=ui.SERIES,
    )

    fig.update_traces(
        textinfo="label",
        textposition="inside",
        insidetextorientation="radial",
        # .values.tolist(): Plotly 6 serializes a 2-D array as base64 bdata,
        # which Streamlit's bundled plotly.js does not decode -- hover shows NaN.
        customdata=summary[["Share %"]].values.tolist(),
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Invested: Rs %{value:,.2f}<br>"
            "Share: %{customdata[0]:.2f}%<extra></extra>"
        ),
        marker=dict(line=dict(width=0)),
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

    k1, k2, k3 = st.columns(3)
    for col, (lbl, val) in zip(
            (k1, k2, k3),
            (("Total invested", f"Rs {total_value:,.2f}"),
             ("Sectors", len(summary)),
             ("Largest", summary.iloc[0]["Sector"] if len(summary) else "-"))):
        with col:
            with st.container(border=True):
                st.metric(lbl, val)

    import plotly.graph_objects as go

    CHART_H = 340  # one height for every chart in this row, so they line up

    left, right = st.columns([1, 1])
    with left:
        st.markdown("##### :material/donut_large: By amount invested")
        with st.container(border=True):
            fig.update_layout(height=CHART_H)
            st.plotly_chart(fig, width="stretch")

    with right:
        st.markdown("##### :material/pie_chart: By number of holdings")
        with st.container(border=True):
            # Money and count answer different questions: one big position can
            # dominate the amount chart while being a single holding.
            counts = go.Figure(go.Pie(
                labels=list(summary["Sector"]), values=list(summary["Holdings"]),
                hole=0.45, sort=False,
                marker=dict(colors=ui.SERIES[:len(summary)], line=dict(width=0)),
                texttemplate="%{label}", textposition="inside",
                insidetextorientation="radial",
                hovertemplate="<b>%{label}</b><br>%{value} holding(s)"
                              "<br>%{percent} of positions<extra></extra>"))
            total_holdings = int(summary["Holdings"].sum() or 0)
            counts.update_layout(
                height=CHART_H, showlegend=False,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                annotations=[dict(text=f"Total<br>{total_holdings} holdings",
                                  x=.5, y=.5, font=dict(size=15), showarrow=False)])
            st.plotly_chart(counts, width="stretch")

    st.markdown("##### :material/bar_chart: Invested by sector")
    with st.container(border=True):
        bar = go.Figure(go.Bar(
            y=list(summary["Sector"]), x=list(summary["Value"]),
            orientation="h", marker_color=ui.BLUE,
            text=[f"Rs {v:,.0f}" for v in summary["Value"]],
            textposition="outside", cliponaxis=False,
            # Without this Plotly prints the raw "(value, label)" tuple.
            hovertemplate="<b>%{y}</b><br>Rs %{x:,.2f} invested<extra></extra>"))
        bar = ui.style_chart(bar, height=90 + 46 * len(summary), title_x="Rs invested")
        # Headroom so the outside labels are not clipped at the plot edge.
        top = float(summary["Value"].max() or 0)
        bar.update_xaxes(range=[0, top * 1.22])
        st.plotly_chart(bar, width="stretch")

    ui.label("Breakdown")
    for _, row in summary.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 2, 2])
            c1.markdown(f"**{row['Sector']}**")
            c1.caption(f"{int(row['Holdings'])} holding(s)")
            c2.caption("Invested")
            c2.write(f"Rs {row['Value']:,.2f}")
            c3.caption("Share")
            c3.html(ui.pill(f"{row['Share %']:.2f}%", "info"))


if __name__ == "__main__":
    sector_user()

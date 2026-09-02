import streamlit as st

from frontend import ui

from frontend.manger_home import require_manager
import pandas as pd
import plotly.express as px

from services.cache import cached_stocks





def sector_manager():
    if not require_manager():
        return

    st.title("Catalog by Sector")
    st.caption("How the stocks you've listed spread across industries.")

    stocks = cached_stocks() or {}
    active = [s for s in stocks.values() if not s.get("is_deleted", False)]

    if not active:
        ui.empty("donut_large", "Nothing to break down",
                "Add a stock to the catalog to see its sector.",
                "Add a stock", "add_stock")
        return

    rows = []
    for stock in active:
        sector = str(stock.get("sector", "Unknown") or "Unknown").strip() or "Unknown"
        rows.append({"Sector": sector, "Stock Count": 1})

    df = pd.DataFrame(rows)
    summary = df.groupby("Sector", as_index=False).agg(
        Stock_Count=("Stock Count", "sum"),
    )

    summary = summary.sort_values("Stock_Count", ascending=False)
    total_count = int(summary["Stock_Count"].sum() or 0)
    summary["Share %"] = summary["Stock_Count"].apply(lambda n: round((n / total_count * 100.0), 2) if total_count > 0 else 0.0)

    fig = px.pie(
        summary,
        names="Sector",
        values="Stock_Count",
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
        # No value line: the catalog stores price 0 for every stock (live prices
        # come from get_prices() at render time), so it would always read Rs 0.00.
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Stocks: %{value}<br>"
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
                text=f"Total<br>{total_count} Stocks",
                x=0.5,
                y=0.5,
                font=dict(size=16),
                showarrow=False,
            )
        ],
    )

    st.plotly_chart(fig, width="stretch")


if __name__ == "__main__":
    sector_manager()

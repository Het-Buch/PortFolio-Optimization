"""Optimization page. Weights render from NumPy first; the council streams after."""

import numpy as np
import pandas as pd
import streamlit as st

from ml.optimization import optimize_portfolio, rebalance_orders
from ml.optimizers import ALGORITHMS
from services.cache import cached_portfolio
from services.stock_services import get_prices, normalize_ticker, display_symbol


def _holdings(active):
    """Collapse repeat purchases of the same ticker into one position."""
    out = {}
    for s in active:
        ticker = normalize_ticker(s.get("ticker"))
        if not ticker:
            continue
        row = out.setdefault(ticker, {
            "company": s.get("company_name") or display_symbol(ticker),
            "ticker": ticker, "quantity": 0, "total_cost": 0.0,
        })
        row["quantity"] += int(s.get("quantity", 0) or 0)
        row["total_cost"] += float(s.get("total_cost", 0) or 0)
    return list(out.values())


def optimize():
    if "user" not in st.session_state:
        st.warning("Please login first.")
        st.session_state["page"] = "login"
        st.rerun()
        return

    st.title("Portfolio Optimization")

    purchased = cached_portfolio(st.session_state["user"]) or {}
    active = [s for s in purchased.values() if not s.get("sold", False)]
    if not active:
        st.warning("No active stocks in portfolio.")
        return

    holdings = _holdings(active)
    prices = get_prices([h["ticker"] for h in holdings])

    for h in holdings:
        live = prices.get(h["ticker"], 0.0)
        avg = h["total_cost"] / h["quantity"] if h["quantity"] else 0.0
        h["price"] = live or avg
        h["position_value"] = h["quantity"] * h["price"]

    st.subheader("Your Portfolio")
    st.dataframe(pd.DataFrame([{
        "Company": h["company"], "Quantity": h["quantity"],
        "Price": round(h["price"], 2), "Value": round(h["position_value"], 2),
    } for h in holdings]), width="stretch", hide_index=True)

    algorithm = st.selectbox("Algorithm", list(ALGORITHMS), index=0)
    compare_all = st.checkbox("Compare all algorithms", value=False)

    if st.button("Optimize", type="primary"):
        with st.spinner("Optimizing..."):
            st.session_state["opt"] = optimize_portfolio(
                {"portfolio": [{"company": h["company"], "ticker": h["ticker"],
                                "stocks_owned": h["quantity"],
                                "position_value": h["position_value"]}
                               for h in holdings]},
                algorithm=algorithm, compare_all=compare_all)
            st.session_state["holdings"] = {
                h["ticker"]: {"quantity": h["quantity"], "company": h["company"]}
                for h in holdings}
            st.session_state["prices"] = {h["ticker"]: h["price"] for h in holdings}
        st.session_state.pop("council", None)

    result = st.session_state.get("opt")
    if not result:
        return

    if result is None:
        st.error("No price history available for these holdings.")
        return

    _render(result)


def _render(result):
    metrics = result["portfolio_metrics"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Expected Return", f"{metrics['expected_return']:.2%}")
    c2.metric("Risk", f"{metrics['portfolio_risk']:.2%}")
    c3.metric("Sharpe", f"{metrics['sharpe_ratio']:.2f}")

    initial = result["initial_weights"]
    optimized = result["portfolio_weights"]
    st.subheader("Suggested Allocation")
    st.dataframe(pd.DataFrame([{
        "Company": name,
        "Current": f"{initial.get(name, 0):.1%}",
        "Suggested": f"{w:.1%}",
        "Change": f"{w - initial.get(name, 0):+.1%}",
        "Action": "BUY" if w > initial.get(name, 0) + 0.01
                  else ("SELL" if w < initial.get(name, 0) - 0.01 else "HOLD"),
    } for name, w in optimized.items()]), width="stretch", hide_index=True)

    orders, leftover = rebalance_orders(
        {t_: w for t_, w in zip(result["tickers_ns"], optimized.values())},
        st.session_state.get("holdings", {}), st.session_state.get("prices", {}))

    if orders:
        st.subheader("What to actually do")
        st.caption("Whole shares only — NSE does not trade fractions.")
        st.dataframe(pd.DataFrame([{
            "Company": o["company"],
            "Hold": o["held"],
            "Target": o["target"],
            "Action": f"{o['action']} {abs(o['delta'])}" if o["delta"] else "HOLD",
            "Price": round(o["price"], 2),
            "Value": round(o["value"], 2),
            "Actual %": f"{o['actual_weight']:.1%}",
        } for o in orders]), width="stretch", hide_index=True)
        if leftover:
            st.caption(f"Uninvested after whole-share rounding: ₹{leftover:,.2f}")

    risk = result.get("risk_metrics") or {}
    if risk:
        r1, r2, r3 = st.columns(3)
        r1.metric("Max Drawdown", f"{risk.get('max_drawdown', 0):.1%}")
        r2.metric("VaR 95%", f"{risk.get('var_95', 0):.2%}")
        r3.metric("Sortino", f"{risk.get('sortino', 0):.2f}")

    if result.get("comparison"):
        st.subheader("Algorithm Comparison")
        st.dataframe(pd.DataFrame([
            {"Algorithm": k, "Sharpe": round(v["sharpe"], 3),
             "Return": f"{v['expected_return']:.2%}", "Risk": f"{v['risk']:.2%}"}
            for k, v in sorted(result["comparison"].items(),
                               key=lambda kv: -kv[1]["sharpe"])
        ]), width="stretch", hide_index=True)

    _council(result)


@st.fragment
def _council(result):
    """Fragment: rerunning the council must not re-run the optimizer above it."""
    st.subheader("Council Analysis")

    if st.button("Convene council"):
        from ml.council import analyze, chair_stream

        tickers = result["tickers"]
        base = np.array(list(result["portfolio_weights"].values()))

        try:
            with st.spinner("Four analysts are pulling live data..."):
                analysis = analyze(tickers, base)
        except Exception as e:
            st.error(f"Council unavailable: {e}")
            st.caption("Weights above are unaffected — they come from the optimizer.")
            return

        for s in analysis["stances"]:
            icon = {"increase": "🟢", "decrease": "🔴", "hold": "⚪"}.get(s["stance"], "⚪")
            with st.expander(f"{icon} {s['role'].title()} — {s['stance']} "
                             f"({s['confidence']}%)"):
                for point in s.get("points") or []:
                    st.write(f"- {point}")
                if s.get("tools_used"):
                    st.caption(f"Tools called: {', '.join(s['tools_used'])}")

        if analysis["unanimous_no_effect"]:
            st.info("All four analysts leaned the same direction, so the "
                    "allocation is unchanged relative to itself — weights are "
                    "relative, and a portfolio-wide tilt has nothing to move "
                    "against. See each analyst's reasoning above.")
        elif analysis["disagreement"]:
            st.caption("Analysts disagreed — the Chair below explains how it "
                      "was resolved.")

        st.subheader("Weight Changes")
        st.dataframe(pd.DataFrame([{
            "Ticker": d["ticker"], "Optimizer": f"{d['optimizer']:.1%}",
            "Council": f"{d['council']:.1%}", "Change": f"{d['change']:+.1%}",
            "Driven by": ", ".join(d["driven_by"]) or "—",
        } for d in analysis["deltas"]]), width="stretch", hide_index=True)

        st.subheader("Chair's Synthesis")
        st.write_stream(chair_stream(analysis))


if __name__ == "__main__":
    optimize()

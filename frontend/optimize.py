"""Optimization page. Weights render from NumPy first; the council streams after."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from ml.optimization import optimize_portfolio, rebalance_orders
from services.cache import cached_portfolio
from services.stock_services import get_prices, normalize_ticker, display_symbol

# Same palette as the landing-page hero, so the app reads as one product.
GOOD, BAD, NEUTRAL, ACCENT = "#2A9D8F", "#B56576", "#4C86C6", "#EAAC8B"


def _rgba(hex_color, alpha):
    """Plotly's marker_color rejects 8-digit hex-alpha (CSS accepts it, Plotly doesn't)."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


def _pill(action):
    color = {"BUY": GOOD, "SELL": BAD}.get(action, NEUTRAL)
    return (f'<span style="background:{color}26;color:{color};'
            f'border:1px solid {color}59;border-radius:999px;padding:.15rem .65rem;'
            f'font-size:.8rem;font-weight:600;white-space:nowrap">{action}</span>')


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
    total_value = sum(h["position_value"] for h in holdings)
    cols = st.columns(min(len(holdings), 4))
    for i, h in enumerate(holdings):
        with cols[i % len(cols)]:
            with st.container(border=True):
                st.caption(display_symbol(h["ticker"]))
                st.markdown(f"**{h['company']}**")
                st.metric("Value", f"₹{h['position_value']:,.2f}")
                share = h["position_value"] / total_value if total_value else 0
                st.caption(f"{h['quantity']} sh @ ₹{h['price']:.2f}  ·  {share:.1%} of portfolio")

    if st.button("Optimize", type="primary"):
        with st.spinner("Trying every optimization strategy..."):
            st.session_state["opt"] = optimize_portfolio(
                {"portfolio": [{"company": h["company"], "ticker": h["ticker"],
                                "stocks_owned": h["quantity"],
                                "position_value": h["position_value"]}
                               for h in holdings]})
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
    if result.get("comparison"):
        st.caption(f"Tried {len(result['comparison'])} optimization strategies — "
                   f"**{metrics['algorithm']}** gave the best risk-adjusted return.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Expected Return", f"{metrics['expected_return']:.2%}")
    c2.metric("Risk", f"{metrics['portfolio_risk']:.2%}")
    c3.metric("Sharpe", f"{metrics['sharpe_ratio']:.2f}")

    initial = result["initial_weights"]
    optimized = result["portfolio_weights"]
    st.subheader("Suggested Allocation")

    names = list(optimized)
    fig = go.Figure()
    fig.add_bar(name="Current", y=names, x=[initial.get(n, 0) * 100 for n in names],
               orientation="h", marker_color=_rgba(NEUTRAL, 0.5))
    fig.add_bar(name="Suggested", y=names, x=[optimized[n] * 100 for n in names],
               orientation="h", marker_color=GOOD)
    fig.update_layout(barmode="group", height=90 + 55 * len(names),
                      margin=dict(l=0, r=10, t=10, b=0),
                      xaxis_title="Weight (%)", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, width="stretch")

    for name, w in optimized.items():
        before = initial.get(name, 0)
        action = ("BUY" if w > before + 0.01 else
                  "SELL" if w < before - 0.01 else "HOLD")
        c1, c2, c3, c4 = st.columns([3, 1.3, 1.3, 1])
        c1.write(name)
        c2.write(f"{before:.1%} → {w:.1%}")
        c3.write(f"{w - before:+.1%}")
        c4.html(_pill(action))

    orders, leftover = rebalance_orders(
        {t_: w for t_, w in zip(result["tickers_ns"], optimized.values())},
        st.session_state.get("holdings", {}), st.session_state.get("prices", {}))

    if orders:
        st.subheader("What to actually do")
        st.caption("Whole shares only — NSE does not trade fractions.")
        for o in orders:
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1.2])
                c1.markdown(f"**{o['company']}**")
                c1.caption(f"{o['held']} → {o['target']} shares  ·  "
                          f"₹{o['price']:.2f}/sh  ·  {o['actual_weight']:.1%} of portfolio")
                c2.write(f"₹{o['value']:,.2f}" if o["delta"] else "")
                c3.html(_pill(o["action"]) if o["delta"] else _pill("HOLD"))
                if o["delta"]:
                    c2.caption(f"{abs(o['delta'])} share(s)")
        if leftover:
            st.caption(f"Uninvested after whole-share rounding: ₹{leftover:,.2f}")

    risk = result.get("risk_metrics") or {}
    if risk:
        st.subheader("Risk Profile")
        with st.container(border=True):
            r1, r2, r3 = st.columns(3)
            r1.metric("Max Drawdown", f"{risk.get('max_drawdown', 0):.1%}")
            r2.metric("VaR 95%", f"{risk.get('var_95', 0):.2%}")
            r3.metric("Sortino", f"{risk.get('sortino', 0):.2f}")

    if result.get("comparison"):
        st.subheader("Algorithm Comparison")
        ranked = sorted(result["comparison"].items(), key=lambda kv: kv[1]["sharpe"])
        best = ranked[-1][0]
        fig = go.Figure(go.Bar(
            y=[k for k, _ in ranked], x=[v["sharpe"] for _, v in ranked],
            orientation="h",
            marker_color=[GOOD if k == best else _rgba(NEUTRAL, 0.5) for k, _ in ranked],
            text=[f"{v['sharpe']:.3f}" for _, v in ranked], textposition="outside",
        ))
        fig.update_layout(height=60 + 42 * len(ranked),
                          margin=dict(l=0, r=30, t=10, b=0), xaxis_title="Sharpe")
        st.plotly_chart(fig, width="stretch")

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

        icon = {"increase": "🟢", "decrease": "🔴", "hold": "⚪"}
        cols = st.columns(len(analysis["stances"]))
        for col, s in zip(cols, analysis["stances"]):
            with col:
                with st.container(border=True):
                    st.markdown(f"{icon.get(s['stance'], '⚪')} **{s['role'].title()}**")
                    st.caption(f"{s['stance'].upper()} · {s['confidence']}% confidence")
                    with st.expander("Reasoning"):
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
        for d in analysis["deltas"]:
            c1, c2, c3, c4 = st.columns([2, 2, 1.2, 2])
            c1.write(d["ticker"])
            c2.write(f"{d['optimizer']:.1%} → {d['council']:.1%}")
            color = GOOD if d["change"] > 0 else BAD if d["change"] < 0 else NEUTRAL
            c3.html(f'<span style="color:{color};font-weight:600">'
                   f'{d["change"]:+.1%}</span>')
            c4.caption(", ".join(d["driven_by"]) or "no tilt")

        st.subheader("Chair's Synthesis")
        st.write_stream(chair_stream(analysis))


if __name__ == "__main__":
    optimize()

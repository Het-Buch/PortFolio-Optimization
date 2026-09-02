"""Optimization page. Weights render from NumPy first; the council streams after."""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from frontend import ui
from ml.optimization import optimize_portfolio, rebalance_orders
from services.cache import cached_portfolio
from services.stock_services import get_prices, normalize_ticker, display_symbol

GOOD, BAD, NEUTRAL = ui.GREEN, ui.RED, ui.BLUE
_rgba = ui.rgba


def _pill(action):
    return ui.pill(action, {"BUY": "good", "SELL": "bad"}.get(action, "neutral"))


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
    st.caption("We test every strategy on your holdings and keep the best one.")

    purchased = cached_portfolio(st.session_state["user"]) or {}
    active = [s for s in purchased.values() if not s.get("sold", False)]
    if not active:
        ui.empty("tune", "Nothing to optimize yet",
                "Buy at least one stock to run the optimizer.",
                "Browse stocks", "buy")
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
        st.caption(f"Tested {len(result['comparison'])} allocation strategies against "
                   "2 years of price history and kept the best risk-adjusted result.")

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

        _schedule(orders, result)

    risk = result.get("risk_metrics") or {}
    if risk:
        st.subheader("Risk Profile")
        with st.container(border=True):
            r1, r2, r3 = st.columns(3)
            r1.metric("Max Drawdown", f"{risk.get('max_drawdown', 0):.1%}")
            r2.metric("VaR 95%", f"{risk.get('var_95', 0):.2%}")
            r3.metric("Sortino", f"{risk.get('sortino', 0):.2f}")

    # Algorithm names are jargon to an investor -- keep the evidence available
    # for anyone who wants it, but never make the user read "PSO" to use the app.
    if result.get("comparison"):
        with st.expander("How this allocation was chosen (technical detail)"):
            ranked = sorted(result["comparison"].items(), key=lambda kv: kv[1]["sharpe"])
            best = ranked[-1][0]
            st.caption(
                f"Every strategy below was run on your holdings. **{best}** scored the "
                "highest Sharpe ratio — return earned per unit of risk taken — so its "
                "allocation is the one shown above.")
            fig = go.Figure(go.Bar(
                y=[k for k, _ in ranked], x=[v["sharpe"] for _, v in ranked],
                orientation="h",
                marker_color=[GOOD if k == best else _rgba(NEUTRAL, 0.5)
                              for k, _ in ranked],
                text=[f"{v['sharpe']:.3f}" for _, v in ranked], textposition="outside",
            ))
            fig.update_layout(height=60 + 42 * len(ranked),
                              margin=dict(l=0, r=30, t=10, b=0), xaxis_title="Sharpe")
            st.plotly_chart(fig, width="stretch")

    _council(result)


TERMS = """
### Terms and Conditions — Scheduled Automatic Rebalancing

**Version 1.0 · Please read in full before accepting.**

By ticking the acceptance box below and selecting "Schedule rebalance", you
("the User") authorise the Portfolio Management System ("the Platform") to
execute the portfolio changes set out above without seeking any further
confirmation from you. Read these terms carefully. If you do not agree with any
part of them, do not accept, and no changes will be scheduled.

**1. Nature of the Platform**

1.1. The Platform is an academic portfolio-management and research application.
It is **not** a broker, exchange, depository participant, investment adviser or
portfolio manager, and it is not registered with the Securities and Exchange
Board of India (SEBI) or any other regulator in any capacity.

1.2. Orders scheduled through this feature are recorded in the Platform's own
database. **They are not routed to any exchange, broker or trading account, and
no real securities are bought or sold.** No real money changes hands and no real
position is created, altered or closed by this feature.

1.3. Prices are obtained from third-party public market-data sources and are
indicative only. They may be delayed, incomplete, adjusted, or wrong.

**2. Authorisation to execute automatically**

2.1. Accepting these terms creates a standing instruction. Once accepted, the
orders listed above are executed by an automated scheduled process **without any
further prompt, notification, confirmation or review**.

2.2. You accept that execution may occur while you are not present, not signed
in, and not otherwise aware that it is taking place.

2.3. The Platform will not contact you before executing, and does not undertake
to notify you after execution. It is your responsibility to check the outcome.

**3. Timing of execution**

3.1. Execution is attempted after the close of the next trading session of the
National Stock Exchange of India ("NSE") following acceptance.

3.2. Execution occurs only on days on which the NSE has actually traded and for
which settled closing data is available. Saturdays, Sundays, declared NSE
holidays, and any unscheduled closure or trading halt are skipped automatically.
Where a day is skipped, the instruction remains pending and is attempted on the
next qualifying day.

3.3. Execution is deliberately performed **after** the 15:30 IST close rather
than at the closing bell, to allow market data to settle. Executing on
unsettled data risks transacting against a price that is later revised.

3.4. No guarantee is given as to the precise time of execution. The scheduled
process is subject to delay, queueing and infrastructure availability outside
the Platform's control.

**4. Prices and quantities**

4.1. **You are agreeing to the share quantities shown above, not to the prices.**
The prices displayed at the time of acceptance are indicative only.

4.2. Orders execute at the closing price of the session on which execution
occurs. That price **will** differ, potentially materially, from the price shown
to you when you accepted, particularly where execution is deferred by holidays
or closures.

4.3. All orders are expressed in whole shares. The NSE does not trade fractional
shares. Quantities are rounded down, which may leave part of your portfolio
value unallocated.

4.4. Where a valid closing price cannot be obtained for every instrument in the
instruction, the entire instruction is deferred rather than partially executed,
so as not to leave the portfolio in an allocation you did not agree to.

**5. Cancellation and amendment**

5.1. You may cancel a scheduled instruction at any time before it executes,
using the cancellation control on this page. Cancellation is immediate and free.

5.2. Scheduling a new instruction automatically supersedes and cancels any
previously scheduled instruction, so that two instructions cannot act against
each other.

5.3. Once execution has begun or completed, the instruction **cannot be
cancelled, reversed, unwound or undone by the Platform**. Any subsequent change
must be made by you as a fresh transaction.

**6. No advice**

6.1. The allocation presented is the output of a numerical optimisation process
and, where applicable, commentary generated by automated language models. It is
provided for informational and educational purposes only.

6.2. Nothing on this page constitutes investment advice, a recommendation, a
solicitation, or an offer to buy or sell any security. No assessment has been
made of your financial situation, objectives, experience, risk tolerance or
suitability.

6.3. You are solely responsible for evaluating the merits and risks of any
allocation before accepting it, and should seek independent, professionally
qualified advice where appropriate.

**7. Risk disclosure**

7.1. Investing in securities carries risk, including the risk of losing the
entire amount invested.

7.2. Past performance, backtested performance and simulated results are **not**
indicators of future results. Optimisation is performed on historical data, and
relationships observed in historical data frequently do not persist.

7.3. Optimised allocations may be concentrated, may increase turnover, and may
underperform a simple equal-weighted or unmanaged portfolio.

7.4. Automated commentary produced by language models may be inaccurate,
incomplete or misleading, notwithstanding the controls applied to it.

**8. Limitation of liability**

8.1. The Platform is provided "as is" and "as available", without warranty of
any kind, express or implied.

8.2. To the maximum extent permitted by law, neither the Platform nor its
authors accept liability for any loss or damage, whether direct, indirect,
incidental, consequential or otherwise, arising from or in connection with: use
of this feature; any executed, delayed, partial or failed instruction; any
inaccuracy in market data; any unavailability or failure of the scheduled
process; or any decision taken in reliance on output produced by the Platform.

8.3. Nothing in these terms excludes liability that cannot lawfully be excluded.

**9. Suspension and changes**

9.1. The Platform may suspend, modify, defer or discontinue automatic execution
at any time, with or without notice, including where market data is unavailable
or unreliable.

9.2. These terms may be amended. Each instruction records the version of the
terms under which it was accepted, and is governed by that version.

**10. Acceptance**

10.1. By ticking the box below you confirm that you have read, understood and
agree to these terms in their entirety; that you are authorised to give this
instruction; and that you understand execution will occur automatically and
without further confirmation.

10.2. Your acceptance is recorded together with the terms version, a timestamp
and the exact instruction accepted.
"""


@st.fragment
def _schedule(orders, result):
    """Accept-and-schedule, or show the pending plan with a way out."""
    from database import rebalance

    user_id = st.session_state["user"]
    st.subheader("Schedule this rebalance")

    pending = rebalance.pending_for(user_id)
    if pending:
        plan = pending[0]
        with st.container(border=True):
            st.markdown(f"**Scheduled** · accepted {plan.get('accepted_at','')}")
            st.caption("Executes after the next NSE close. Cancel any time "
                       "before then.")
            for o in plan.get("orders", []):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(o.get("company") or o.get("ticker"))
                c2.caption(f"{o.get('held_at_plan')} → {o.get('target')} shares")
                c3.html(_pill(o.get("action", "HOLD")))
            if st.button("Cancel scheduled rebalance", icon=":material/close:"):
                if rebalance.cancel(plan.get("plan_id"), user_id):
                    st.toast("Rebalance cancelled")
                    st.rerun(scope="fragment")
                else:
                    st.error("Could not cancel — it may have already executed.")
        return

    actionable = [o for o in orders if o.get("delta")]
    if not actionable:
        st.caption("Nothing to schedule — your portfolio already matches the target.")
        return

    # Fixed height: the terms scroll inside their own box instead of pushing the
    # acceptance control off-screen.
    with st.container(border=True, height=340):
        st.markdown(TERMS)

    with st.container(border=True):
        st.caption(f"Terms version {rebalance.TERMS_VERSION} · "
                   f"{len(actionable)} order(s) will execute automatically.")
        agreed = st.checkbox("I have read and accept the Terms and Conditions "
                             "above, and authorise automatic execution.")
        if st.button("Schedule rebalance", type="primary", disabled=not agreed,
                     icon=":material/event_available:"):
            plan_id = rebalance.create_plan(
                user_id, actionable,
                algorithm=(result.get("portfolio_metrics") or {}).get("algorithm", ""))
            if plan_id:
                st.toast("Rebalance scheduled for the next trading day")
                st.rerun(scope="fragment")
            else:
                st.error("Nothing to schedule.")


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

        stance_kind = {"increase": "good", "decrease": "bad"}
        cols = st.columns(len(analysis["stances"]))
        for col, s in zip(cols, analysis["stances"]):
            with col:
                with st.container(border=True):
                    st.markdown(f"**{s['role'].title()}**")
                    st.html(ui.pill(s["stance"].upper(), stance_kind.get(s["stance"], "neutral")))
                    st.caption(f"{s['confidence']}% confidence")
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

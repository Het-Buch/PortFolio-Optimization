import plotly.graph_objects as go
import streamlit as st
from services.cache import cached_user, cached_portfolio, cached_transactions
from services.stock_services import get_prices, display_symbol
from database.curd import sell_stock

from frontend import ui


def _pending_rebalance_notice(user_id):
    """Something that will trade on its own must be visible from the home page,
    not only from the page it was scheduled on."""
    from database import rebalance

    try:
        pending = rebalance.pending_for(user_id)
    except Exception:
        return
    if not pending:
        return

    plan = pending[0]
    orders = plan.get("orders", [])
    buys = sum(1 for o in orders if int(o.get("delta", 0) or 0) > 0)
    sells = sum(1 for o in orders if int(o.get("delta", 0) or 0) < 0)

    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        c1.markdown("**:material/event_repeat: Rebalance scheduled**")
        c1.caption(f"{buys} buy / {sells} sell order(s) execute automatically "
                   "after the next market close. Cancel any time before then.")
        if c2.button("Review", width="stretch", icon=":material/tune:"):
            st.session_state["page"] = "optimize"
            st.rerun()


def home():

    if "user" not in st.session_state:
        st.warning("You are not logged in.")
        st.session_state["page"] = "login"
        st.rerun()
        return

    user_id = st.session_state["user"]

    user_details = cached_user(user_id)
    name = user_details.get("name")

    st.title(f"Hi, {name}")
    st.caption("Your portfolio at a glance.")

    _pending_rebalance_notice(user_id)

    # Navigation lives in landing.py's role-driven sidebar. A second copy here
    # duplicated every button, and its Logout skipped session_ui.end(), leaving
    # the Firebase token and cookie alive so a refresh logged you straight back in.

    purchased = cached_portfolio(user_id)

    if not purchased:
        ui.empty("account_balance_wallet", "No holdings yet",
                "Buy your first stock and it will show up here with live "
                "valuation and profit tracking.", "Browse stocks", "buy")
        return

    active_stocks = {
        k: v for k, v in purchased.items() if not v.get("sold", False)
    }

    if not active_stocks:
        ui.empty("inventory_2", "No active holdings",
                "Everything you owned has been sold. Buy again to start tracking.",
                "Browse stocks", "buy")
        return

    grouped_stocks = {}
    for purchase_id, stock in active_stocks.items():
        group_key = stock.get("stock_id") or stock.get("ticker") or purchase_id
        if group_key not in grouped_stocks:
            grouped_stocks[group_key] = {
                "company_name": stock.get("company_name", ""),
                "ticker": stock.get("ticker", ""),
                "quantity": 0,
                "total_cost": 0.0,
                "target_set": False,
                "target_price": 0.0,
                "purchase_ids": []
            }

        grouped_stocks[group_key]["quantity"] += int(stock.get("quantity", 0) or 0)
        grouped_stocks[group_key]["total_cost"] += float(stock.get("total_cost", 0) or 0)
        grouped_stocks[group_key]["purchase_ids"].append(purchase_id)

        stock_target_set = bool(stock.get("target_set", False))
        stock_target_price = float(stock.get("target_price", 0) or 0)
        if stock_target_set and stock_target_price > 0:
            grouped_stocks[group_key]["target_set"] = True
            if grouped_stocks[group_key]["target_price"] == 0:
                grouped_stocks[group_key]["target_price"] = stock_target_price

    ticker_list = [
        str(s.get("ticker", "")).strip().upper()
        for s in grouped_stocks.values()
        if str(s.get("ticker", "")).strip()
    ]
    prices = get_prices(ticker_list) if ticker_list else {}

    stock_data = []
    display_prices = {}
    total_cost = 0
    auto_sold = []

    for stock_key, stock in grouped_stocks.items():
        ticker = str(stock.get("ticker", "")).strip().upper()
        market_price = 0

        if ticker:
            ticker_ns = ticker if ticker.endswith(".NS") else ticker + ".NS"
            market_price = round(prices.get(ticker_ns, 0) or 0, 2)

        quantity = int(stock.get("quantity", 0) or 0)
        stored_price = float(stock.get("total_cost", 0) or 0) / quantity if quantity > 0 else 0
        derived_price = float(stock.get("total_cost", 0) or 0) / quantity if quantity > 0 else 0
        avg_buy_price = round(stored_price or derived_price, 2)
        sell_check_price = round(market_price or avg_buy_price, 2)
        display_prices[stock_key] = sell_check_price

        target_price = round(float(stock.get("target_price", 0) or 0), 2)
        target_set = bool(stock.get("target_set", False))

        if target_set and target_price > 0 and sell_check_price > 0 and sell_check_price >= target_price:
            sold_any = False
            for purchase_id in stock.get("purchase_ids", []):
                if sell_stock(purchase_id, user_id, sell_check_price, mode="auto"):
                    sold_any = True

            if sold_any:
                sold_name = stock.get("company_name") or display_symbol(ticker)
                auto_sold.append(f"{sold_name} @ ₹{sell_check_price:.2f}")
                continue

        total = float(stock.get("total_cost", 0) or 0)
        display_company_name = stock.get("company_name") or display_symbol(ticker)
        stock_data.append({
            "company": display_company_name,
            "ticker": display_symbol(ticker),
            "quantity": quantity,
            "avg_price": avg_buy_price,
            "market_price": sell_check_price,
            "invested": total,
            "value": quantity * sell_check_price,
            "target": target_price if target_set else None,
        })
        if total > 0:
            total_cost += total

    if auto_sold:
        cached_portfolio.clear()
        cached_transactions.clear()  # a sell writes a transaction row too
        st.success("Auto-sell executed for: " + ", ".join(auto_sold))
        st.rerun()

    total_value = sum(s["value"] for s in stock_data)
    pnl = total_value - total_cost
    pnl_pct = (pnl / total_cost) if total_cost else 0

    ui.label("Overview")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        with st.container(border=True):
            st.metric("Invested", f"₹{total_cost:,.2f}")
    with k2:
        with st.container(border=True):
            st.metric("Current Value", f"₹{total_value:,.2f}")
    with k3:
        with st.container(border=True):
            st.metric("Profit / Loss", f"₹{pnl:,.2f}", f"{pnl_pct:+.2%}")
    with k4:
        with st.container(border=True):
            st.metric("Holdings", len(stock_data))

    left, right = st.columns([1, 1])
    with left:
        st.markdown("##### :material/donut_large: Allocation")
        with st.container(border=True):
            fig = go.Figure(go.Pie(
                labels=[s["company"] for s in stock_data],
                values=[s["value"] for s in stock_data],
                hole=0.66, marker=dict(colors=ui.SERIES[:len(stock_data)],
                                       line=dict(width=0)),
                textinfo="percent",
                hovertemplate="%{label}<br>₹%{value:,.2f}<extra></extra>",
            ))
            st.plotly_chart(ui.style_chart(fig, legend=True), width="stretch")

    with right:
        st.markdown("##### :material/bar_chart: Gain / loss by stock")
        with st.container(border=True):
            gains = [s["value"] - s["invested"] for s in stock_data]
            fig = go.Figure(go.Bar(
                y=[s["company"] for s in stock_data], x=gains, orientation="h",
                marker_color=[ui.GREEN if g >= 0 else ui.RED for g in gains],
                text=[f"₹{g:,.0f}" for g in gains], textposition="outside",
            ))
            st.plotly_chart(ui.style_chart(fig, title_x="₹ gain / loss"),
                           width="stretch")

    ui.label("Your holdings")
    for s in stock_data:
        gain = s["value"] - s["invested"]
        gain_pct = (gain / s["invested"]) if s["invested"] else 0
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
            c1.markdown(f"**{s['company']}**")
            c1.caption(f"{s['ticker']}  ·  {s['quantity']} shares")
            c2.caption("Avg → Market")
            c2.write(f"₹{s['avg_price']:,.2f} → ₹{s['market_price']:,.2f}")
            c3.caption("Value")
            c3.write(f"₹{s['value']:,.2f}")
            c4.caption("Gain / loss")
            c4.html(ui.money(gain, ui.GREEN if gain >= 0 else ui.RED)
                   + f' <span style="opacity:.75">({gain_pct:+.1%})</span>')
            if s["target"]:
                c1.caption(f":material/flag: Target ₹{s['target']:,.2f}")

    st.divider()

    stock_map = {}
    label_counts = {}
    for key, value in grouped_stocks.items():
        display_ticker = display_symbol(value.get("ticker", ""))
        display_name = value.get("company_name") or display_ticker
        base_label = f"{display_name} ({display_ticker})" if display_ticker else display_name
        count = label_counts.get(base_label, 0) + 1
        label_counts[base_label] = count
        label = base_label if count == 1 else f"{base_label} #{count}"
        stock_map[label] = (key, value)

    ui.label("Manage a position")
    selected = st.selectbox("Select stock", list(stock_map.keys()))

    stock_id, stock = stock_map[selected]

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Set target price", width="stretch",
                     icon=":material/flag:"):
            st.session_state.selected_stock = stock.get("purchase_ids", [None])[0]
            st.session_state.page = "edit_stock"
            st.rerun()

    with col2:
        if st.button("Sell position", width="stretch", type="primary",
                     icon=":material/sell:"):

            success = False
            sell_price = display_prices.get(stock_id, 0)
            for purchase_id in stock.get("purchase_ids", []):
                if sell_stock(
                    purchase_id,
                    user_id,
                    sell_price,
                    mode="manual"
                ):
                    success = True

            if success:
                cached_portfolio.clear()
                cached_transactions.clear()  # a sell writes a transaction row too
                st.toast("Stock sold successfully")
                st.rerun()
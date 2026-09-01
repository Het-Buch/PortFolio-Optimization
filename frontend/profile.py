import plotly.graph_objects as go
import streamlit as st

from frontend import ui
from services.cache import cached_transactions, cached_user
from services.stock_services import display_symbol


def profile():

    # Login check
    if "user" not in st.session_state:
        st.warning("Please login first.")
        st.session_state["page"] = "login"
        st.rerun()
        return

    user_id = st.session_state["user"]
    user_details = cached_user(user_id)

    if not user_details:
        ui.empty("person_off", "Profile unavailable",
                "We could not load your account details.")
        return

    st.title("Profile")
    st.caption("Your account and full transaction history.")

    name = user_details.get("name") or "—"
    initial = str(name)[:1].upper()

    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 3, 2])
        c1.html(
            f'<div style="width:64px;height:64px;border-radius:50%;'
            f'background:linear-gradient(135deg,{ui.BLUE},{ui.GREEN});'
            f'display:flex;align-items:center;justify-content:center;'
            f'color:#fff;font-size:1.6rem;font-weight:700">{initial}</div>')
        c2.markdown(f"### {name}")
        c2.caption(f":material/mail: {user_details.get('email') or '—'}")
        c3.caption(":material/call: Phone")
        c3.write(user_details.get("phone") or "—")
        c3.caption(f":material/badge: {user_id}")

    ui.label("Transaction history")
    transactions = cached_transactions(user_id)

    if not transactions:
        ui.empty("receipt_long", "No transactions yet",
                "Your buys and sells will appear here.", "Buy a stock", "buy")
        return

    buys = [t for t in transactions if t.get("action") == "BUY"]
    sells = [t for t in transactions if t.get("action") == "SELL"]
    invested = sum(float(t.get("total_value", 0) or 0) for t in buys)
    realised = sum(float(t.get("total_value", 0) or 0) for t in sells)

    k1, k2, k3, k4 = st.columns(4)
    for col, (lbl, val) in zip(
            (k1, k2, k3, k4),
            (("Transactions", len(transactions)), ("Buys", len(buys)),
             ("Sells", len(sells)), ("Net flow", f"₹{realised - invested:,.2f}"))):
        with col:
            with st.container(border=True):
                st.metric(lbl, val)

    if buys or sells:
        with st.container(border=True):
            fig = go.Figure(go.Bar(
                x=["Bought", "Sold"], y=[invested, realised],
                marker_color=[ui.BLUE, ui.GREEN],
                text=[f"₹{invested:,.0f}", f"₹{realised:,.0f}"],
                textposition="outside"))
            st.plotly_chart(ui.style_chart(fig, height=240), width="stretch")

    for t in sorted(transactions, key=lambda x: str(x.get("timestamp", "")),
                    reverse=True):
        action = str(t.get("action", "")).upper()
        company = t.get("company_name") or display_symbol(t.get("ticker", ""))
        qty = t.get("quantity", 0)
        price = float(t.get("price_per_stock", 0) or 0)
        total = float(t.get("total_value", 0) or 0)
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2.6, 1.4, 2, 1.4])
            c1.markdown(f"**{company}**")
            c1.caption(f"{display_symbol(t.get('ticker', ''))}  ·  "
                      f"{t.get('timestamp', '')}")
            c2.html(ui.pill(action, "good" if action == "BUY" else "bad"))
            c2.caption(str(t.get("mode", "")))
            c3.caption("Quantity × price")
            c3.write(f"{qty} × ₹{price:,.2f}")
            c4.caption("Total")
            c4.write(f"₹{total:,.2f}")


if __name__ == "__main__":
    profile()

import streamlit as st

from database.curd import get_stock_data, set_target_price
from services.cache import cached_portfolio


@st.cache_data(ttl=10)
def load_stock(stock_id):
    return get_stock_data(stock_id)


def edit_stock():
    if "user" not in st.session_state:
        st.warning("Please login first.")
        st.session_state["page"] = "login"
        st.rerun()
        return

    st.title("Set Target Price")

    if st.button("Back", width="stretch", icon=":material/arrow_back:"):
        st.session_state["page"] = "home"
        st.rerun()

    purchased_id = st.session_state.get("selected_stock")

    if not purchased_id:
        st.error("No stock selected.")
        st.session_state["page"] = "home"
        st.rerun()
        return

    stock_data = load_stock(purchased_id)

    if not stock_data:
        st.error("Stock not found.")
        return

    stock_name = st.text_input(
        "Stock Name",
        value=stock_data.get("company_name", ""),
        disabled=True
    )

    stock_ticker = st.text_input(
        "Stock Ticker",
        value=stock_data.get("ticker", ""),
        disabled=True
    )

    stock_price = st.number_input(
        "Bought Price",
        value=round(float(stock_data.get("price_per_stock", 0.0)), 2),
        step=0.01,
        format="%.2f",
        disabled=True
    )

    quantity = st.number_input(
        "Number of Stocks",
        value=int(stock_data.get("quantity", 1)),
        min_value=1,
        step=1,
        disabled=True
    )

    # A bare number box gave no way to judge what a sensible target even is.
    from services.stock_services import get_prices, normalize_ticker

    ticker = normalize_ticker(stock_data.get("ticker"))
    live = float((get_prices([ticker]) or {}).get(ticker, 0) or 0)
    qty = int(stock_data.get("quantity", 0) or 0)
    buy = float(stock_data.get("price_per_stock", 0) or 0)
    reference = live or buy

    st.divider()
    st.markdown("##### Set an auto-sell target")
    st.caption("The whole position sells automatically after market close on "
               "the first day the price closes at or above your target.")

    m1, m2, m3 = st.columns(3)
    m1.metric("You paid", f"₹{buy:,.2f}")
    m2.metric("Market now", f"₹{live:,.2f}" if live else "—")
    if live and buy:
        m3.metric("Unrealised", f"{(live - buy) / buy:+.1%}")

    if reference:
        st.caption("Common choices, based on the current price:")
        picks = st.columns(4)
        for col, pct in zip(picks, (5, 10, 20, 30)):
            price = round(reference * (1 + pct / 100), 2)
            if col.button(f"+{pct}%\n₹{price:,.2f}", key=f"tgt{pct}",
                          width="stretch"):
                st.session_state["target_pick"] = price
                st.rerun()

    target_default = round(float(stock_data.get("target_price", 0.0) or 0.0), 2)
    target_default = float(st.session_state.pop("target_pick", target_default))

    target_price = st.number_input(
        "Target Price (Auto Sell)",
        value=target_default,
        min_value=0.0,
        step=0.01,
        format="%.2f"
    )

    if target_price > 0 and reference:
        move = (target_price - reference) / reference
        if target_price <= reference:
            st.warning(f"That is at or below the current price, so it would "
                       f"sell at the very next check — effectively selling now. "
                       f"Set it above ₹{reference:,.2f} to wait for a gain.",
                       icon=":material/warning:")
        else:
            gain = (target_price - buy) * qty if buy else 0
            st.info(f"Needs a {move:+.1%} move from here. If it hits, you would "
                    f"sell {qty} share(s) for ₹{target_price * qty:,.2f}"
                    + (f", a profit of ₹{gain:,.2f}." if buy else "."),
                    icon=":material/info:")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Set Target"):

            if target_price <= 0:
                st.error("Target price must be greater than 0.")
                return

            success = set_target_price(
                purchased_id,
                target_price,
                st.session_state["user"]
            )

            if success:
                cached_portfolio.clear()
                st.toast("Target price set successfully")
                st.session_state["page"] = "home"
                st.rerun()

            else:
                st.error("Update failed.")

    with col2:
        if st.button("Cancel", width="stretch", icon=":material/close:"):
            st.session_state["page"] = "home"
            st.rerun()


if __name__ == "__main__":
    edit_stock()
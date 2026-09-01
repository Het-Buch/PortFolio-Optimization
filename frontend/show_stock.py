import streamlit as st

from frontend import ui
from frontend.manger_home import require_manager
from services.cache import cached_stocks
from services.stock_services import display_symbol
from database.manager_operation import delete_stock_from_db


def show_stocks():
    if not require_manager():
        return

    st.title("Catalog")
    st.caption("Stocks users can buy. Name and sector come from market data.")

    stocks = cached_stocks()
    if not stocks:
        ui.empty("storefront", "Catalog is empty",
                "Add a ticker and the rest resolves automatically.",
                "Add a stock", "add_stock")
        return

    live = [(sid, s) for sid, s in stocks.items()
            if not s.get("is_deleted", False)]
    if not live:
        ui.empty("inventory_2", "No active stocks",
                "Every entry has been removed.", "Add a stock", "add_stock")
        return

    sectors = {}
    for _, s in live:
        key = str(s.get("sector", "Unknown") or "Unknown")
        sectors[key] = sectors.get(key, 0) + 1

    k1, k2 = st.columns(2)
    with k1:
        with st.container(border=True):
            st.metric("Listed stocks", len(live))
    with k2:
        with st.container(border=True):
            st.metric("Sectors covered", len(sectors))

    query = st.text_input("Search", placeholder="Company, ticker or sector...",
                          label_visibility="collapsed")
    shown = live
    if query:
        q = query.lower().strip()
        shown = [(sid, s) for sid, s in live
                 if q in str(s.get("name", "")).lower()
                 or q in str(s.get("ticker", "")).lower()
                 or q in str(s.get("sector", "")).lower()]
        if not shown:
            ui.empty("search_off", "No matches", f"Nothing matched “{query}”.")
            return

    ui.label(f"{len(shown)} stock(s)")
    for sid, s in sorted(shown, key=lambda kv: str(kv[1].get("name", ""))):
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 1.6, 1.6, 1.2])
            c1.markdown(f"**{s.get('name') or display_symbol(s.get('ticker', ''))}**")
            c1.caption(f":material/tag: {display_symbol(s.get('ticker', ''))}")
            c2.html(ui.pill(str(s.get("sector", "Unknown") or "Unknown"), "info"))
            c3.caption("Added")
            c3.caption(str(s.get("added_on", "—"))[:10])
            with c4:
                b1, b2 = st.columns(2)
                if b1.button("", key=f"edit_{sid}", icon=":material/edit:",
                             help="Edit this stock"):
                    st.session_state["selected_stock"] = sid
                    st.session_state["page"] = "edit_stock_manager"
                    st.rerun()
                if b2.button("", key=f"del_{sid}", icon=":material/delete:",
                             help="Remove from catalog"):
                    if delete_stock_from_db(sid):
                        cached_stocks.clear()
                        st.toast("Stock removed")
                        st.rerun()
                    st.error("Failed to delete stock.")


if __name__ == "__main__":
    show_stocks()

import streamlit as st

from frontend import ui
from frontend.manger_home import require_manager
from services.cache import cached_users


def show_users():

    # Safe session check
    if not require_manager():
        return

    st.title("Users")
    st.caption("Everyone registered on the platform.")

    users = cached_users()

    if not users:
        ui.empty("group_off", "No users yet",
                "Registrations will appear here as they come in.")
        return

    rows = [u.get("personal", {}) | {"_login": u.get("login", {})}
            for u in users.values() if u]
    blocked = sum(1 for r in rows if r.get("blocked"))

    k1, k2, k3 = st.columns(3)
    for col, (lbl, val) in zip((k1, k2, k3),
                               (("Total users", len(rows)),
                                ("Active", len(rows) - blocked),
                                ("Blocked", blocked))):
        with col:
            with st.container(border=True):
                st.metric(lbl, val)

    query = st.text_input("Search", placeholder="Name, email or user ID...",
                          label_visibility="collapsed")
    if query:
        q = query.lower().strip()
        rows = [r for r in rows
                if q in str(r.get("name", "")).lower()
                or q in str(r.get("email", "")).lower()
                or q in str(r.get("user_id", "")).lower()]
        if not rows:
            ui.empty("search_off", "No matches", f"Nothing matched “{query}”.")
            return

    ui.label(f"{len(rows)} user(s)")
    for r in rows:
        name = r.get("name") or "—"
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([0.5, 3, 2.2, 1.3])
            c1.html(
                f'<div style="width:38px;height:38px;border-radius:50%;'
                f'background:linear-gradient(135deg,{ui.BLUE},{ui.GREEN});'
                f'display:flex;align-items:center;justify-content:center;'
                f'color:#fff;font-weight:700">{str(name)[:1].upper()}</div>')
            c2.markdown(f"**{name}**")
            c2.caption(f":material/mail: {r.get('email') or '—'}")
            c3.caption(f":material/badge: {r.get('user_id') or '—'}")
            c3.caption(f":material/call: {r.get('phone') or '—'}")
            c4.html(ui.pill("BLOCKED", "bad") if r.get("blocked")
                    else ui.pill("ACTIVE", "good"))
            last = (r.get("_login") or {}).get("last_login_date")
            c4.caption(f"Last seen {last}" if last else "Never signed in")

            uid = r.get("user_id")
            is_blocked = bool(r.get("blocked"))
            if c4.button("Unblock" if is_blocked else "Block", key=f"blk_{uid}",
                         width="stretch",
                         icon=":material/lock_open:" if is_blocked else ":material/block:"):
                st.session_state["confirm_block"] = (uid, name, is_blocked)
                st.rerun()

    target = st.session_state.get("confirm_block")
    if target:
        _confirm_block(*target)


@st.dialog("Change account access")
def _confirm_block(uid, name, is_blocked):
    from database.manager_operation import set_user_blocked

    if is_blocked:
        st.write(f"Restore access for **{name}** ({uid})?")
        st.caption("They will be able to sign in again immediately.")
    else:
        st.write(f"Block **{name}** ({uid})?")
        st.warning("They will be signed out of new sessions and cannot log in. "
                   "Their holdings and history are kept untouched.")

    c1, c2 = st.columns(2)
    if c1.button("Confirm", type="primary", width="stretch"):
        ok = set_user_blocked(uid, not is_blocked)
        st.session_state.pop("confirm_block", None)
        if ok:
            cached_users.clear()
            st.toast("Access restored" if is_blocked else "User blocked")
        else:
            st.toast("Could not update that user")
        st.rerun()
    if c2.button("Cancel", width="stretch"):
        st.session_state.pop("confirm_block", None)
        st.rerun()


if __name__ == "__main__":
    show_users()

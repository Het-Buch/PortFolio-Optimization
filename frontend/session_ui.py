"""Cookie <-> session_state bridge. Keeps login alive across a page refresh."""

import streamlit as st

from database import session as sess


def _cookies():
    """A thin wrapper -- state lives in the browser, keyed by `key`, not here.

    Must not be cached: stx.CookieManager() renders a component (a widget, in
    Streamlit's terms), and a cached function's body is skipped on a cache hit,
    so the widget silently never renders and every cookie read returns None.
    """
    import extra_streamlit_components as stx
    return stx.CookieManager(key="pms_cookies")


def _get(name):
    try:
        return _cookies().get(name)
    except Exception:
        return None


def restore():
    """Rehydrate session_state from the cookie. Call once, before routing."""
    if st.session_state.get("user"):
        return True

    token = _get(sess.COOKIE_NAME)
    if not token:
        return False

    user_id, is_manager = sess.resolve(token)
    if not user_id:
        return False

    st.session_state["user"] = "manager" if is_manager else user_id
    st.session_state["token"] = token
    sess.refresh(token)  # slide expiry on activity
    return True


def start(user_id, is_manager=False):
    """Create the session and set the cookie. Cookie carries the token only."""
    token, expires = sess.create(user_id, is_manager)
    st.session_state["user"] = "manager" if is_manager else user_id
    st.session_state["token"] = token
    try:
        _cookies().set(sess.COOKIE_NAME, token, expires_at=expires,
                       same_site="strict", secure=True, key="set_session")
    except Exception:
        pass  # cookie unavailable -> session still works until refresh


def end():
    sess.destroy(st.session_state.get("token"))
    try:
        _cookies().delete(sess.COOKIE_NAME, key="del_session")
    except Exception:
        pass
    for key in ("user", "token", "opt", "council", "selected_stock"):
        st.session_state.pop(key, None)

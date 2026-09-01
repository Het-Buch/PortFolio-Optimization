"""Router + role-driven sidebar. Pages are imported lazily so startup stays fast."""

import streamlit as st

USER_NAV = [("Home", "home", ":material/dashboard:"),
            ("Buy Stocks", "buy", ":material/add_shopping_cart:"),
            ("Optimize", "optimize", ":material/tune:"),
            ("Sectors", "sector_user", ":material/donut_large:"),
            ("Profile", "profile", ":material/person:")]

MANAGER_NAV = [("Dashboard", "manager_home", ":material/analytics:"),
               ("Add Stock", "add_stock", ":material/add_circle:"),
               ("Stocks", "show_stocks", ":material/inventory_2:"),
               ("Users", "show_users", ":material/group:"),
               ("Sectors", "sector_manager", ":material/donut_large:")]

PAGES = {
    "home": ("frontend.home", "home"),
    "buy": ("frontend.buy", "buy"),
    "optimize": ("frontend.optimize", "optimize"),
    "profile": ("frontend.profile", "profile"),
    "sector_user": ("frontend.sector_user", "sector_user"),
    "edit_stock": ("frontend.edit_stock", "edit_stock"),
    "login": ("frontend.login", "login"),
    "register": ("frontend.register", "register"),
    "manager_home": ("frontend.manger_home", "manager_home"),
    "add_stock": ("frontend.add_stock", "add_stock"),
    "show_stocks": ("frontend.show_stock", "show_stocks"),
    "show_users": ("frontend.show_users", "show_users"),
    "sector_manager": ("frontend.sector_manager", "sector_manager"),
    "edit_stock_manager": ("frontend.edit_stock_manager", "edit_stock_manager"),
}


def go(page):
    st.session_state["page"] = page
    st.rerun()


def _logout():
    from frontend.session_ui import end
    end()
    go("landing")


def _sidebar():
    user = st.session_state.get("user")
    if not user:
        return

    is_manager = user == "manager"
    st.sidebar.title("Manager" if is_manager else "Menu")

    current = st.session_state.get("page")
    for label, page, icon in (MANAGER_NAV if is_manager else USER_NAV):
        if st.sidebar.button(label, width="stretch", icon=icon,
                             type="primary" if page == current else "secondary"):
            go(page)

    st.sidebar.divider()
    if st.sidebar.button("Logout", width="stretch", icon=":material/logout:"):
        _logout()


def _hero():
    """Inline SVG: currentColor inherits Streamlit's text color, so it flips theme."""
    st.html("""
<style>
  .hero{display:flex;flex-direction:column;align-items:center;gap:.25rem;margin:.5rem 0 1.5rem}
  .hero svg{width:100%;max-width:620px;height:auto;color:inherit;opacity:.95}
  .hero .grid{stroke:currentColor;opacity:.12}
  .hero .axis{stroke:currentColor;opacity:.35}
  .hero .frontier{fill:none;stroke:url(#g1);stroke-width:3;stroke-linecap:round;
    stroke-dasharray:520;stroke-dashoffset:520;animation:draw 2.2s ease-out forwards}
  .hero .area{fill:url(#g2);opacity:0;animation:fade .9s ease-out 1.4s forwards}
  .hero .dot{fill:url(#g1);opacity:0;animation:pop .5s cubic-bezier(.2,1.6,.4,1) forwards}
  .hero .spark{fill:none;stroke:currentColor;opacity:.28;stroke-width:2;stroke-linecap:round}
  .hero .ring{fill:none;stroke-width:9;stroke-linecap:round;transform-origin:center;
    stroke-dasharray:0 999;animation:arc 1.1s ease-out forwards}
  @keyframes draw{to{stroke-dashoffset:0}}
  @keyframes fade{to{opacity:1}}
  @keyframes pop{to{opacity:1}}
  @keyframes arc{to{stroke-dasharray:var(--len) 999}}
  @keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}
  .hero .drift{animation:float 5s ease-in-out infinite}
  @media (prefers-reduced-motion:reduce){.hero *{animation:none!important;
    stroke-dashoffset:0!important;opacity:1!important}}
</style>
<div class="hero">
<svg viewBox="0 0 620 240" role="img" aria-label="Risk-return frontier with optimized allocation">
  <defs>
    <linearGradient id="g1" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0%" stop-color="#2A9D8F"/><stop offset="55%" stop-color="#4C86C6"/>
      <stop offset="100%" stop-color="#B56576"/>
    </linearGradient>
    <linearGradient id="g2" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#4C86C6" stop-opacity=".28"/>
      <stop offset="100%" stop-color="#4C86C6" stop-opacity="0"/>
    </linearGradient>
  </defs>

  <g class="grid">
    <line x1="60" y1="40"  x2="430" y2="40"/><line x1="60" y1="90"  x2="430" y2="90"/>
    <line x1="60" y1="140" x2="430" y2="140"/><line x1="60" y1="190" x2="430" y2="190"/>
  </g>
  <line class="axis" x1="60" y1="200" x2="430" y2="200"/>
  <line class="axis" x1="60" y1="30"  x2="60"  y2="200"/>

  <path class="area" d="M60 190 C140 150 200 90 280 62 C340 44 390 38 430 36 L430 200 L60 200 Z"/>
  <path class="frontier" d="M60 190 C140 150 200 90 280 62 C340 44 390 38 430 36"/>

  <circle class="dot" cx="128" cy="158" r="5"  style="animation-delay:1.5s"/>
  <circle class="dot" cx="205" cy="112" r="5"  style="animation-delay:1.7s"/>
  <circle class="dot" cx="286" cy="61"  r="7.5" style="animation-delay:1.9s"/>
  <circle class="dot" cx="366" cy="43"  r="5"  style="animation-delay:2.1s"/>

  <g class="spark" opacity=".3">
    <path d="M300 52 L286 61 M286 61 L272 74"/>
  </g>

  <g class="drift" transform="translate(530,118)">
    <circle class="ring" r="42" stroke="#2A9D8F" style="--len:96;animation-delay:2.0s"
            transform="rotate(-90)"/>
    <circle class="ring" r="42" stroke="#4C86C6" style="--len:72;animation-delay:2.15s"
            transform="rotate(41)"/>
    <circle class="ring" r="42" stroke="#B56576" style="--len:56;animation-delay:2.3s"
            transform="rotate(148)"/>
    <circle class="ring" r="42" stroke="#EAAC8B" style="--len:40;animation-delay:2.45s"
            transform="rotate(232)"/>
  </g>

  <text x="245" y="228" font-size="11" fill="currentColor" opacity=".45"
        text-anchor="middle" font-family="system-ui,sans-serif">risk &#8594;</text>
  <text x="30" y="118" font-size="11" fill="currentColor" opacity=".45"
        text-anchor="middle" font-family="system-ui,sans-serif"
        transform="rotate(-90 30 118)">return &#8594;</text>
</svg>
</div>
""")


def _landing():
    st.title("Portfolio Management System")
    st.caption("ML forecasting, nature-inspired optimization, and an agent council "
               "that argues the allocation before you see it.")

    _hero()

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        col1, col2 = st.columns(2)
        if col1.button("Login", width="stretch", type="primary",
                       icon=":material/login:"):
            go("login")
        if col2.button("Register", width="stretch", icon=":material/person_add:"):
            go("register")

    st.divider()
    features = [
        (":material/tune:", "Smart optimization",
         "Seven strategies compete on your holdings; the best risk-adjusted one wins."),
        (":material/groups:", "Analyst council",
         "Four AI analysts pull live data, debate, and a chair resolves the call."),
        (":material/monitoring:", "Live NSE data",
         "Batched quotes, news sentiment and full risk metrics on every position."),
    ]
    cols = st.columns(3)
    for col, (icon, title, body) in zip(cols, features):
        with col:
            with st.container(border=True):
                st.markdown(f"### {icon}")
                st.markdown(f"**{title}**")
                st.caption(body)

    st.divider()
    # No privilege granted here -- the manager flag is set only after authentication.
    if st.button("Manager login", icon=":material/admin_panel_settings:"):
        go("login")


def landing():
    st.session_state.setdefault("page", "landing")

    # One injection here covers every page the router dispatches to.
    from frontend.ui import inject
    inject()

    # Rehydrate from cookie so a refresh does not bounce the user to login.
    from frontend.session_ui import restore
    restore()

    page = st.session_state["page"]

    _sidebar()

    if page == "landing":
        _landing()
        return

    module_name, fn_name = PAGES.get(page, (None, None))
    if not module_name:
        go("landing")
        return

    import importlib
    getattr(importlib.import_module(module_name), fn_name)()

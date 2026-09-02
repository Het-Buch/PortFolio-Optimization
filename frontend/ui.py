"""Shared design system. One palette, one card style, one chart theme.

Icons are Streamlit's built-in Material Symbols (":material/name:"), not emoji.
Font Awesome was the ask, but st.html runs its input through DOMPurify, which
drops <link> tags -- a CDN stylesheet is silently stripped and never loads.
Material Symbols are real vector icons, ship with Streamlit, and work in
markdown, button icon=, metric label= and alert icon= without a CDN.
"""

import streamlit as st

# Green + blue, as asked. Warm tones only ever signal loss.
GREEN = "#10B981"
GREEN_DIM = "#34D399"
BLUE = "#3B82F6"
BLUE_DIM = "#60A5FA"
RED = "#F43F5E"
SLATE = "#64748B"

# Categorical order for pies and multi-series charts. 12 entries, because the
# catalog already has 10 sectors -- at 8 the sequence wrapped and two slices
# came out the same colour. Adjacent entries alternate cool-blue and green and
# also step in lightness, so neighbouring slices separate on hue *and* value,
# not hue alone (a pure blue/green alternation still reads flat when six of the
# twelve are the same blue at different opacities).
SERIES = [
    BLUE,        # 3B82F6  blue
    GREEN,       # 10B981  emerald
    "#A78BFA",   # violet
    GREEN_DIM,   # 34D399  mint
    BLUE_DIM,    # 60A5FA  sky
    "#14B8A6",   # teal
    "#818CF8",   # indigo
    "#6EE7B7",   # pale green
    "#0EA5E9",   # cyan
    "#22C55E",   # green
    "#93C5FD",   # pale blue
    "#2DD4BF",   # turquoise
]


def rgba(hex_color, alpha):
    """Plotly's marker_color rejects 8-digit hex-alpha; CSS accepts it."""
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r},{g},{b},{alpha})"


def inject():
    """Global styling. Called once per page, before anything renders."""
    st.html("""
<style>
  /* Tighten Streamlit's default vertical rhythm -- the stock spacing is what
     makes a page of widgets read as a form rather than a product. */
  .block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1180px;}
  h1 {font-weight: 700; letter-spacing: -0.02em;}
  h2, h3 {font-weight: 650; letter-spacing: -0.01em; margin-top: .4rem;}

  /* Cards: bordered containers get a subtle lift and a hover state. */
  div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px;
    transition: border-color .15s ease, transform .15s ease;
  }
  div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(59,130,246,.45);
  }

  /* Metrics read as the headline number they are. */
  div[data-testid="stMetricValue"] {font-size: 1.55rem; font-weight: 680;}
  div[data-testid="stMetricLabel"] {opacity: .72; font-size: .82rem;
    text-transform: uppercase; letter-spacing: .04em;}

  /* Buttons: rounded, with a real primary colour rather than Streamlit red. */
  .stButton > button {border-radius: 10px; font-weight: 600;}
  .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #3B82F6, #10B981);
    border: none; color: #fff;
  }
  .stButton > button[kind="primary"]:hover {filter: brightness(1.07);}

  /* Inputs */
  .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
    border-radius: 10px;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {gap: .25rem;}
  .stTabs [data-baseweb="tab"] {border-radius: 9px 9px 0 0; font-weight: 600;}

  /* Section label used above card groups. */
  .sec-label {font-size:.78rem; letter-spacing:.09em; text-transform:uppercase;
    opacity:.6; font-weight:700; margin:.2rem 0 .5rem;}
</style>
""")


def pill(text, kind="neutral"):
    """Small status badge. kind: good | bad | neutral | info."""
    color = {"good": GREEN, "bad": RED, "info": BLUE}.get(kind, SLATE)
    return (f'<span style="background:{rgba(color, .14)};color:{color};'
            f'border:1px solid {rgba(color, .38)};border-radius:999px;'
            f'padding:.16rem .68rem;font-size:.78rem;font-weight:650;'
            f'white-space:nowrap">{text}</span>')


def money(value, color=None):
    """Rupee figure, optionally coloured by sign."""
    if color is None:
        return f"₹{value:,.2f}"
    return (f'<span style="color:{color};font-weight:650">₹{value:,.2f}</span>')


def signed(value, suffix="", pct=False):
    """Coloured +/- figure. Green up, red down, slate flat."""
    color = GREEN if value > 0 else RED if value < 0 else SLATE
    text = f"{value:+.2%}" if pct else f"{value:+,.2f}{suffix}"
    return f'<span style="color:{color};font-weight:650">{text}</span>'


def label(text):
    st.html(f'<div class="sec-label">{text}</div>')


def style_chart(fig, height=300, legend=False, title_x=None):
    """One chart look everywhere: no chartjunk, tight margins, subtle grid."""
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=18, t=10, b=0),
        showlegend=legend,
        legend=dict(orientation="h", y=-0.12, x=0),
        xaxis_title=title_x,
        font=dict(size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font_size=12),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(128,128,128,.15)", zeroline=False)
    fig.update_yaxes(showgrid=False, zeroline=False)
    return fig


def empty(icon, title, body, action_label=None, action_page=None):
    """A real empty state instead of a bare st.info box."""
    with st.container(border=True):
        st.markdown(f"### :material/{icon}: {title}")
        st.caption(body)
        if action_label and action_page:
            if st.button(action_label, type="primary"):
                st.session_state["page"] = action_page
                st.rerun()

"""Market data: the only yfinance caller. Batched downloads; .info on catalog writes only."""

import logging

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

UNKNOWN_SECTOR = "Unknown"
_MISSING = {"", "none", "null", "nan", "n/a", "na", "unknown"}


def normalize_ticker(ticker):
    """Uppercase + ensure .NS suffix. Returns '' for empty input."""
    t = str(ticker or "").strip().upper()
    if not t:
        return ""
    return t if t.endswith(".NS") else f"{t}.NS"


def display_symbol(ticker):
    return str(ticker or "").strip().upper().replace(".NS", "")


def normalize_sector(sector):
    text = str(sector or "").strip()
    return UNKNOWN_SECTOR if text.lower() in _MISSING else text


def _key(tickers):
    """Normalize, dedupe, sort. Sorting makes the cache key order-independent."""
    if isinstance(tickers, str):
        tickers = [tickers]
    return tuple(sorted({normalize_ticker(t) for t in (tickers or [])} - {""}))


@st.cache_data(ttl=300, show_spinner=False)
def _download(symbols, period):
    if not symbols:
        return pd.DataFrame()
    import yfinance as yf  # lazy: ~1s import, not needed to render a page
    try:
        raw = yf.download(list(symbols), period=period, auto_adjust=True,
                          progress=False, threads=False)
    except Exception as e:
        logger.warning("download failed %s: %s", symbols, e)
        return pd.DataFrame()
    if raw is None or raw.empty:
        return pd.DataFrame()

    # yfinance gives MultiIndex columns for many tickers, flat for one.
    if isinstance(raw.columns, pd.MultiIndex):
        if "Close" not in raw.columns.get_level_values(0):
            return pd.DataFrame()
        close = raw["Close"]
    else:
        if "Close" not in raw.columns:
            return pd.DataFrame()
        close = raw[["Close"]]
        close.columns = [symbols[0]]
    return close.dropna(how="all")


def get_history(tickers, period="2y"):
    """DataFrame of adjusted closes, one column per ticker. One HTTP call."""
    symbols = _key(tickers)
    if not symbols:
        return pd.DataFrame()
    hist = _download(symbols, period)
    if hist.empty:
        return hist
    cols = [t for t in symbols if t in hist.columns]
    return hist[cols] if cols else pd.DataFrame()


def get_prices(tickers):
    """{ticker: last_close}. Missing tickers are absent; never raises."""
    hist = get_history(tickers, period="5d")
    out = {}
    for sym in hist.columns:
        s = hist[sym].dropna()
        if not s.empty:
            out[sym] = float(s.iloc[-1])
    return out


def get_price(ticker):
    sym = normalize_ticker(ticker)
    return float(get_prices([sym]).get(sym, 0.0)) if sym else 0.0


@st.cache_data(ttl=86400, show_spinner=False)
def get_profile(ticker):
    """Name + sector for one ticker. Uses .info -- catalog writes only.

    resolved=False means the ticker could not be confirmed; callers should treat
    that as validation failure, not a reason to store placeholder data.
    """
    sym = normalize_ticker(ticker)
    miss = {"ticker": sym, "name": display_symbol(sym),
            "sector": UNKNOWN_SECTOR, "resolved": False}
    if not sym:
        return miss
    import yfinance as yf
    try:
        info = yf.Ticker(sym).info or {}
    except Exception as e:
        logger.warning("profile failed %s: %s", sym, e)
        return miss

    name = str(info.get("longName") or info.get("shortName") or "").strip()
    if not name:
        return miss
    return {"ticker": sym, "name": name,
            "sector": normalize_sector(info.get("sector")), "resolved": True}


def ticker_exists(ticker):
    """True when the symbol returns real price data. The only check worth doing --
    length/charset rules reject valid symbols and accept invented ones."""
    sym = normalize_ticker(ticker)
    return bool(sym) and not get_history([sym], period="5d").empty

import requests
import streamlit as st
import yfinance as yf

BASE_URL = "https://query1.finance.yahoo.com/v7/finance/quote?symbols="

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def _normalize_ticker(ticker):
    ticker = str(ticker).strip().upper()
    if not ticker:
        return ""
    return ticker if ticker.endswith(".NS") else f"{ticker}.NS"


def _fetch_from_yahoo_quote_api(tickers):
    query = ",".join(tickers)
    url = BASE_URL + query

    r = requests.get(url, headers=HEADERS, timeout=5)
    if r.status_code != 200:
        return {}, {}

    try:
        data = r.json()
    except Exception:
        return {}, {}

    results = data.get("quoteResponse", {}).get("result", [])

    prices = {}
    names = {}

    for item in results:
        symbol = str(item.get("symbol", "")).upper()
        price = item.get("regularMarketPrice")
        name = item.get("longName") or item.get("shortName") or symbol.replace(".NS", "")

        if symbol:
            names[symbol] = name
            if price is not None:
                prices[symbol] = float(price)

    return prices, names


def _fetch_from_yfinance(tickers):
    prices = {}
    names = {}

    for symbol in tickers:
        try:
            ticker_obj = yf.Ticker(symbol)
            fast_info = getattr(ticker_obj, "fast_info", {}) or {}

            price = fast_info.get("lastPrice")
            if price is None:
                history = ticker_obj.history(period="1d")
                if not history.empty and "Close" in history.columns:
                    price = float(history["Close"].iloc[-1])

            info = getattr(ticker_obj, "info", {}) or {}
            name = info.get("longName") or info.get("shortName") or symbol.replace(".NS", "")

            names[symbol] = name

            if price is not None:
                prices[symbol] = float(price)
        except Exception:
            continue

    return prices, names

@st.cache_data(ttl=20)
def fetch_stock_data(tickers):
    """
    Fetch live stock prices for NSE symbols.
    Returns symbol->price mapping and, for single ticker calls,
    includes "price", "name", and "symbol" keys for UI compatibility.
    """

    try:

        if isinstance(tickers, str):
            tickers = [tickers]

        normalized_tickers = [_normalize_ticker(t) for t in tickers]
        normalized_tickers = [t for t in normalized_tickers if t]

        if not normalized_tickers:
            return {}

        # preserve order, remove duplicates
        normalized_tickers = list(dict.fromkeys(normalized_tickers))

        prices, names = _fetch_from_yahoo_quote_api(normalized_tickers)

        missing = [t for t in normalized_tickers if t not in prices]
        if missing:
            fallback_prices, fallback_names = _fetch_from_yfinance(missing)
            prices.update(fallback_prices)
            names.update(fallback_names)

        response = {k: float(v) for k, v in prices.items()}

        if len(normalized_tickers) == 1:
            symbol = normalized_tickers[0]
            response["symbol"] = symbol
            response["price"] = float(prices.get(symbol, 0) or 0)
            response["name"] = names.get(symbol, symbol.replace(".NS", ""))

        if not response:
            return {}

        return response

    except Exception as e:
        print("Stock fetch error:", e)
        return {}
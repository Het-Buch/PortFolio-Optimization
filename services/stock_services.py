import requests
import streamlit as st
import yfinance as yf

BASE_URL = "https://query1.finance.yahoo.com/v7/finance/quote?symbols="

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def _normalize_sector(sector):
    text = str(sector or "").strip()
    if not text or text.lower() in {"none", "null", "nan", "n/a", "na", "unknown"}:
        return "Unknown"
    return text


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
        if price is None:
            price = item.get("postMarketPrice")
        if price is None:
            price = item.get("preMarketPrice")
        if price is None:
            price = item.get("previousClose")
        name = item.get("longName") or item.get("shortName") or symbol.replace(".NS", "")

        if symbol:
            names[symbol] = name
            if price is not None:
                prices[symbol] = float(price)

    return prices, names


def _fetch_from_yfinance(tickers):
    prices = {}
    names = {}
    sectors = {}

    for symbol in tickers:
        try:
            ticker_obj = yf.Ticker(symbol)
            fast_info = getattr(ticker_obj, "fast_info", {}) or {}

            price = (
                fast_info.get("lastPrice")
                or fast_info.get("regularMarketPrice")
                or fast_info.get("previousClose")
            )
            if price is None:
                info = getattr(ticker_obj, "info", {}) or {}
                price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")

            if price is None:
                history = ticker_obj.history(period="5d", auto_adjust=False)
                if not history.empty and "Close" in history.columns:
                    price = float(history["Close"].iloc[-1])

            info = getattr(ticker_obj, "info", {}) or {}
            name = info.get("longName") or info.get("shortName") or symbol.replace(".NS", "")
            sector = _normalize_sector(info.get("sector"))

            names[symbol] = name
            sectors[symbol] = sector

            if price is not None:
                prices[symbol] = float(price)
        except Exception:
            continue

    return prices, names, sectors

@st.cache_data(ttl=120)
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

        sectors = {}

        missing = [t for t in normalized_tickers if t not in prices]
        if missing:
            fallback_prices, fallback_names, fallback_sectors = _fetch_from_yfinance(missing)
            prices.update(fallback_prices)
            names.update(fallback_names)
            sectors.update(fallback_sectors)

        response = {k: float(v) for k, v in prices.items()}
        response["name_map"] = names
        response["sector_map"] = sectors

        if len(normalized_tickers) == 1:
            symbol = normalized_tickers[0]

            # For add/edit flows we need sector metadata even when quote API already returned price.
            sector_now = _normalize_sector(sectors.get(symbol, "Unknown"))
            if sector_now == "Unknown":
                extra_prices, extra_names, extra_sectors = _fetch_from_yfinance([symbol])
                prices.update(extra_prices)
                names.update(extra_names)
                sectors.update(extra_sectors)

            response["symbol"] = symbol
            response["price"] = float(prices.get(symbol, 0) or 0)
            response["name"] = names.get(symbol, symbol.replace(".NS", ""))
            response["sector"] = _normalize_sector(sectors.get(symbol, "Unknown"))

        if not response:
            return {}

        return response

    except Exception as e:
        print("Stock fetch error:", e)
        return {}
import yfinance as yf
import streamlit as st

@st.cache_data(ttl=60)
def fetch_stock_data(tickers):

    try:

        # Ensure list
        if isinstance(tickers, str):
            tickers = [tickers]

        # Ensure NSE suffix
        tickers = [
            t if t.endswith(".NS") else t + ".NS"
            for t in tickers
        ]

        data = yf.download(
            tickers,
            period="1d",
            interval="1m",
            progress=False,
            group_by="ticker",
            threads=False
        )

        prices = {}

        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    prices[ticker] = float(data["Close"].iloc[-1])
                else:
                    prices[ticker] = float(data[ticker]["Close"].iloc[-1])
            except:
                prices[ticker] = None

        return prices

    except Exception as e:
        print("Stock fetch error:", e)
        return {}
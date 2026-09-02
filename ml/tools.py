"""Tools the council agents can call. This is what makes them agents, not prompts."""

import json

import numpy as np
import streamlit as st

from ml import optimizers
from services.stock_services import get_history, get_prices, display_symbol

# Results are trimmed before they enter context — raw frames blow the token budget.
MAX_HEADLINES = 5


def get_quote(tickers):
    """Latest close for one or more tickers."""
    if isinstance(tickers, str):
        tickers = [tickers]
    prices = get_prices(tickers)
    if not prices:
        return {"error": "no price data returned"}
    return {display_symbol(t): round(p, 2) for t, p in prices.items()}


def get_price_history(ticker, period="6mo"):
    """Summary stats over a window — not the raw series, which would flood context."""
    hist = get_history([ticker], period=period)
    if hist.empty:
        return {"error": f"no history for {ticker}"}

    col = hist.columns[0]
    s = hist[col].dropna()
    if len(s) < 2:
        return {"error": f"insufficient history for {ticker}"}

    rets = s.pct_change().dropna()
    curve = (1 + rets).cumprod()
    return {
        "ticker": display_symbol(col),
        "period": period,
        "first": round(float(s.iloc[0]), 2),
        "last": round(float(s.iloc[-1]), 2),
        "return_pct": round(float(s.iloc[-1] / s.iloc[0] - 1) * 100, 2),
        "annual_vol_pct": round(float(rets.std() * np.sqrt(252)) * 100, 2),
        "max_drawdown_pct": round(float((curve / curve.cummax() - 1).min()) * 100, 2),
        "days": int(len(s)),
    }


def get_news_sentiment(company):
    """Scraped headlines + VADER score for a company."""
    from ml.news import filter_data
    data = filter_data(company)
    headlines = [n["headline"] for n in data.get("news", [])][:MAX_HEADLINES]
    return {
        "company": company,
        "sentiment": round(float(data.get("sentiment", 0) or 0), 3),
        "headline_count": len(data.get("news", [])),
        "headlines": headlines,
        "note": data.get("message", ""),
    }


@st.cache_data(ttl=300, show_spinner=False)
def run_optimizer(tickers, algorithm="PSO"):
    """Optimal weights for a ticker set under one algorithm.

    Cached: several agents hold this tool, and re-running seven swarms over
    identical inputs inside one debate is pure waste. TTL matches the price
    cache, so results never outlive the data they came from.
    """
    hist = get_history(tickers, period="2y")
    if hist.empty:
        return {"error": "no history for optimization"}

    w, stats = optimizers.optimize(hist, algorithm=algorithm)
    if not len(w):
        return {"error": "optimization produced no weights"}

    return {
        "algorithm": algorithm,
        "weights": {display_symbol(t): round(float(x), 4)
                    for t, x in zip(hist.columns, w)},
        "expected_return_pct": round(stats["expected_return"] * 100, 2),
        "risk_pct": round(stats["risk"] * 100, 2),
        "sharpe": round(stats["sharpe"], 3),
    }


@st.cache_data(ttl=300, show_spinner=False)
def compare_algorithms(tickers):
    """All seven algorithms on the same problem, ranked by Sharpe.

    The most expensive tool in the registry, and both bear and quant can call
    it in the same debate -- cache it or pay for it twice.
    """
    hist = get_history(tickers, period="2y")
    if hist.empty:
        return {"error": "no history for comparison"}

    results = optimizers.compare(hist)
    ranked = sorted(results.items(), key=lambda kv: -kv[1]["sharpe"])
    return {
        "ranked": [
            {"algorithm": name,
             "sharpe": round(r["sharpe"], 3),
             "return_pct": round(r["expected_return"] * 100, 2),
             "risk_pct": round(r["risk"] * 100, 2)}
            for name, r in ranked
        ],
        "best": ranked[0][0] if ranked else None,
    }


REGISTRY = {
    "get_quote": get_quote,
    "get_price_history": get_price_history,
    "get_news_sentiment": get_news_sentiment,
    "run_optimizer": run_optimizer,
    "compare_algorithms": compare_algorithms,
}

SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_quote",
        "description": "Latest closing price for one or more NSE tickers.",
        "parameters": {"type": "object", "properties": {
            "tickers": {"type": "array", "items": {"type": "string"},
                        "description": "NSE symbols, e.g. ['TCS', 'INFY']"}},
            "required": ["tickers"]}}},

    {"type": "function", "function": {
        "name": "get_price_history",
        "description": "Return, volatility and max drawdown for one ticker over a window.",
        "parameters": {"type": "object", "properties": {
            "ticker": {"type": "string"},
            "period": {"type": "string", "enum": ["1mo", "3mo", "6mo", "1y", "2y"]}},
            "required": ["ticker"]}}},

    {"type": "function", "function": {
        "name": "get_news_sentiment",
        "description": "Recent financial headlines and sentiment score for a company.",
        "parameters": {"type": "object", "properties": {
            "company": {"type": "string"}}, "required": ["company"]}}},

    {"type": "function", "function": {
        "name": "run_optimizer",
        "description": "Optimal portfolio weights for a ticker set using one algorithm.",
        "parameters": {"type": "object", "properties": {
            "tickers": {"type": "array", "items": {"type": "string"}},
            "algorithm": {"type": "string",
                          "enum": list(optimizers.ALGORITHMS.keys())}},
            "required": ["tickers"]}}},

    {"type": "function", "function": {
        "name": "compare_algorithms",
        "description": "Run every optimizer on the same tickers and rank by Sharpe.",
        "parameters": {"type": "object", "properties": {
            "tickers": {"type": "array", "items": {"type": "string"}}},
            "required": ["tickers"]}}},
]

# Each agent only sees the tools its role needs — smaller context, fewer stray calls.
ROLE_TOOLS = {
    "bull": ["get_price_history", "get_news_sentiment", "get_quote"],
    "bear": ["get_price_history", "get_news_sentiment", "compare_algorithms"],
    "quant": ["run_optimizer", "compare_algorithms", "get_price_history"],
    "macro": ["get_news_sentiment", "get_price_history", "get_quote"],
}


def schemas_for(role=None):
    if not role:
        return SCHEMAS
    allowed = set(ROLE_TOOLS.get(role, []))
    return [s for s in SCHEMAS if s["function"]["name"] in allowed]


def call(name, arguments):
    """Run one tool. Errors come back as data so the model can react, not crash."""
    fn = REGISTRY.get(name)
    if not fn:
        return {"error": f"unknown tool {name}"}
    try:
        args = json.loads(arguments) if isinstance(arguments, str) else (arguments or {})
        return fn(**args)
    except Exception as e:
        return {"error": f"{name} failed: {e}"}


def _self_check():
    assert set(REGISTRY) == {s["function"]["name"] for s in SCHEMAS}, "registry/schema mismatch"
    for role, names in ROLE_TOOLS.items():
        assert set(names) <= set(REGISTRY), f"{role} references unknown tool"
        assert schemas_for(role), f"{role} has no tools"
    assert call("nope", "{}")["error"].startswith("unknown tool")
    assert "error" in call("get_quote", '{"bad_arg": 1}')
    print("tools: OK")


if __name__ == "__main__":
    _self_check()

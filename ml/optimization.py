"""Portfolio optimization entry point. Deterministic path only — no LLM here."""

import numpy as np

from ml import optimizers
from services.stock_services import get_history, normalize_ticker, display_symbol


def current_weights(portfolio):
    """Weights implied by what the user actually holds, by position value."""
    values = [float(c.get("position_value", 0) or 0) for c in portfolio]
    total = sum(values)

    if total <= 0:  # fall back to share count when prices are unavailable
        values = [float(c.get("stocks_owned", 0) or 0) for c in portfolio]
        total = sum(values)
    if total <= 0:
        n = max(len(portfolio), 1)
        return {c.get("company", "?"): 1.0 / n for c in portfolio}

    return {c.get("company", "?"): v / total for c, v in zip(portfolio, values)}


def optimize_portfolio(portfolio_data, algorithm=None):
    """Weights + metrics for a portfolio.

    algorithm=None (the default, and what the app always uses): run every
    algorithm and keep whichever wins on Sharpe. The user never picks PSO vs.
    GWO by name -- the backend decides, and the comparison table is the
    evidence for why. Pass an explicit algorithm only to force one, e.g. in a
    script or test.
    """
    portfolio = portfolio_data.get("portfolio", [])
    if not portfolio:
        return None

    tickers = [normalize_ticker(c.get("ticker")) for c in portfolio]
    by_ticker = {t: c for t, c in zip(tickers, portfolio) if t}

    history = get_history([t for t in tickers if t], period="2y")
    if history.empty:
        return None

    comparison = None
    if algorithm:
        weights, stats = optimizers.optimize(history, algorithm=algorithm)
    else:
        ranked = optimizers.compare(history)
        if not ranked:
            # Single ticker: compare() needs >=2 assets to have anything to rank.
            weights, stats = optimizers.optimize(history)
        else:
            comparison = ranked
            best_name, best = max(ranked.items(), key=lambda kv: kv[1]["sharpe"])
            weights = best["weights"]
            stats = {"expected_return": best["expected_return"], "risk": best["risk"],
                     "sharpe": best["sharpe"], "algorithm": best_name}

    if not len(weights):
        return None

    # history.columns is the authority — a ticker with no data is silently dropped.
    names = [by_ticker.get(t, {}).get("company") or display_symbol(t)
             for t in history.columns]

    result = {
        "portfolio_weights": {n: float(w) for n, w in zip(names, weights)},
        "portfolio_metrics": {
            "expected_return": stats["expected_return"],
            "portfolio_risk": stats["risk"],
            "sharpe_ratio": stats["sharpe"],
            "algorithm": stats["algorithm"],
        },
        "risk_metrics": optimizers.risk_metrics(weights, history),
        "initial_weights": current_weights(portfolio),
        "tickers": [display_symbol(t) for t in history.columns],
        "tickers_ns": list(history.columns),
        "history": history,
    }

    if comparison:
        result["comparison"] = {
            name: {"sharpe": r["sharpe"],
                   "expected_return": r["expected_return"],
                   "risk": r["risk"]}
            for name, r in comparison.items()
        }

    return result


def rebalance_orders(weights, holdings, prices):
    """Turn target weights into whole-share orders. NSE has no fractional shares."""
    total = sum(int(h.get("quantity", 0) or 0) * float(prices.get(t, 0) or 0)
                for t, h in holdings.items())
    if total <= 0:
        return [], 0.0

    orders = []
    spent = 0.0
    for ticker, holding in holdings.items():
        price = float(prices.get(ticker, 0) or 0)
        held = int(holding.get("quantity", 0) or 0)
        target_weight = float(weights.get(ticker, 0) or 0)
        if price <= 0:
            continue

        # Floor, never round up: rounding up can demand cash the user does not have.
        target_shares = int((target_weight * total) // price)
        delta = target_shares - held
        spent += target_shares * price

        orders.append({
            "ticker": ticker,
            "company": holding.get("company", ticker),
            "price": price,
            "held": held,
            "target": target_shares,
            "delta": delta,
            "action": "BUY" if delta > 0 else ("SELL" if delta < 0 else "HOLD"),
            "value": target_shares * price,
            "actual_weight": (target_shares * price / total) if total else 0.0,
            "target_weight": target_weight,
        })

    return orders, round(total - spent, 2)


def _self_check():
    import pandas as pd
    rng = np.random.default_rng(0)
    idx = pd.date_range("2024-01-01", periods=300, freq="B")
    prices = pd.DataFrame(
        100 * np.cumprod(1 + rng.normal(0.0005, 0.012, size=(300, 3)), axis=0),
        columns=["A.NS", "B.NS", "C.NS"], index=idx)

    w, stats = optimizers.optimize(prices, algorithm="PSO")
    assert abs(w.sum() - 1) < 1e-6 and (w >= 0).all(), w
    assert set(stats) == {"expected_return", "risk", "sharpe", "algorithm"}

    pf = [{"company": "A", "ticker": "A", "stocks_owned": 10, "position_value": 100},
          {"company": "B", "ticker": "B", "stocks_owned": 5, "position_value": 300}]
    init = current_weights(pf)
    assert abs(sum(init.values()) - 1) < 1e-9 and init["B"] > init["A"], init

    # No position values -> falls back to share count, still normalized.
    init = current_weights([{"company": "A", "ticker": "A", "stocks_owned": 3},
                            {"company": "B", "ticker": "B", "stocks_owned": 1}])
    assert abs(init["A"] - 0.75) < 1e-9, init
    holdings = {"A.NS": {"quantity": 10, "company": "A"},
                "B.NS": {"quantity": 10, "company": "B"}}
    px = {"A.NS": 100.0, "B.NS": 300.0}          # total = 1000 + 3000 = 4000
    orders, cash = rebalance_orders({"A.NS": 0.5, "B.NS": 0.5}, holdings, px)

    by = {o["ticker"]: o for o in orders}
    assert by["A.NS"]["target"] == 20, by["A.NS"]   # 2000 / 100
    assert by["B.NS"]["target"] == 6, by["B.NS"]    # floor(2000 / 300)
    assert by["A.NS"]["action"] == "BUY" and by["A.NS"]["delta"] == 10
    assert by["B.NS"]["action"] == "SELL" and by["B.NS"]["delta"] == -4
    assert all(float(o["target"]).is_integer() for o in orders), "fractional shares"
    assert cash == 200.0, cash                      # 4000 - 2000 - 1800 left over

    assert rebalance_orders({}, {}, {}) == ([], 0.0)
    print("optimization: OK")


if __name__ == "__main__":
    _self_check()

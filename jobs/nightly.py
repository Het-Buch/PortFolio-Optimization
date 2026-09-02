"""Nightly cron: auto-sell on target, snapshot values, cache closes."""

import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from firebase_admin import db

from database.connection import initialize_firebase
from database.curd import sell_stock
from services.stock_services import (get_history, get_prices, normalize_ticker,
                                     prices_are_stale)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nightly")

IST = timezone(timedelta(hours=5, minutes=30))


def _today():
    """IST, not UTC -- an NSE trading day is an IST calendar day."""
    return datetime.now(IST).strftime("%Y-%m-%d")


def last_session(ticker="RELIANCE.NS"):
    """Date of the most recent NSE session Yahoo has, or None."""
    hist = get_history([ticker], period="5d")
    if hist.empty:
        return None
    return hist.index[-1].strftime("%Y-%m-%d")


def traded_today():
    """False on weekends, NSE holidays, and before Yahoo settles the close."""
    # Without this the job stamps the last session's prices with today's date.
    session = last_session()
    if session is None:
        log.error("could not determine last session")
        return False
    if session != _today():
        log.info("no session today (latest is %s) -- market holiday or not settled",
                 session)
        return False
    return True


def _open_purchases():
    rows = db.reference("purchases").get() or {}
    return {k: v for k, v in rows.items() if v and not v.get("sold")}


def auto_sell(purchases, prices):
    """Sell every holding whose target has been reached."""
    sold = 0
    for pid, p in purchases.items():
        if not p.get("target_set"):
            continue
        target = float(p.get("target_price", 0) or 0)
        price = prices.get(normalize_ticker(p.get("ticker")), 0.0)
        if target > 0 and price >= target:
            if sell_stock(pid, p.get("user_id"), price, mode="auto"):
                log.info("sold %s @ %.2f (target %.2f)", pid, price, target)
                sold += 1
    return sold


def execute_rebalances(prices):
    """Run every accepted rebalance at today's close.

    Only reached after traded_today() and the stale-price drop, so a plan can
    never execute on a holiday or against a cached price. Sells run before buys
    so the portfolio is never momentarily over-allocated.
    """
    from database import rebalance
    from database.curd import add_purchase_to_db, sell_quantity

    done = 0
    for plan in rebalance.all_pending():
        plan_id = plan.get("plan_id")
        user_id = plan.get("user_id")
        orders = plan.get("orders") or []

        # Every ticker must have a live close. Executing half a plan would
        # leave the portfolio somewhere the user never agreed to.
        missing = [o["ticker"] for o in orders
                   if not prices.get(normalize_ticker(o.get("ticker")))]
        if missing:
            log.warning("plan %s deferred: no price for %s", plan_id, ", ".join(missing))
            continue

        if not rebalance.claim(plan_id):
            log.info("plan %s already claimed elsewhere", plan_id)
            continue

        filled, failed = [], []
        try:
            for o in sorted(orders, key=lambda x: int(x.get("delta", 0) or 0)):
                ticker = normalize_ticker(o.get("ticker"))
                price = float(prices.get(ticker, 0) or 0)
                delta = int(o.get("delta", 0) or 0)

                if delta < 0:
                    n = sell_quantity(user_id, ticker, -delta, price, mode="rebalance")
                    (filled if n == -delta else failed).append(
                        {"ticker": ticker, "action": "SELL", "shares": n, "price": price})
                elif delta > 0:
                    ok = add_purchase_to_db(
                        user_id=user_id, company_name=o.get("company", ticker),
                        quantity=delta, price_per_stock=price,
                        total_cost=round(delta * price, 2),
                        stock_id=o.get("stock_id", ""), ticker=ticker)
                    (filled if ok else failed).append(
                        {"ticker": ticker, "action": "BUY", "shares": delta, "price": price})

            status = rebalance.EXECUTED if not failed else rebalance.FAILED
            rebalance.finish(plan_id, status, {"filled": filled, "failed": failed,
                                               "executed_on": _today()})
            log.info("plan %s %s: %d filled, %d failed",
                     plan_id, status, len(filled), len(failed))
            done += 1
        except Exception as e:
            rebalance.finish(plan_id, rebalance.FAILED,
                             {"error": str(e), "filled": filled, "executed_on": _today()})
            log.error("plan %s crashed: %s", plan_id, e)

    return done


def snapshot(purchases, prices):
    """Write today's value per user. Enables real performance charts."""
    totals = {}
    for p in purchases.values():
        uid = p.get("user_id")
        if not uid:
            continue
        qty = int(p.get("quantity", 0) or 0)
        price = prices.get(normalize_ticker(p.get("ticker")), 0.0)
        cost = float(p.get("total_cost", 0) or 0)
        agg = totals.setdefault(uid, {"value": 0.0, "cost": 0.0})
        agg["value"] += qty * price
        agg["cost"] += cost

    day = _today()
    for uid, agg in totals.items():
        agg["pnl"] = round(agg["value"] - agg["cost"], 2)
        agg["value"] = round(agg["value"], 2)
        agg["cost"] = round(agg["cost"], 2)
        db.reference(f"snapshots/{uid}/{day}").set(agg)
    return len(totals)


def cache_prices(prices):
    """Store closes so page loads read Firebase, not Yahoo."""
    if not prices:
        return 0
    db.reference("price_cache").set({
        "date": _today(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "prices": {t.replace(".", "_"): round(p, 2) for t, p in prices.items()},
    })
    return len(prices)


def _catalog_tickers():
    """Every live catalog ticker, so the cache covers stocks nobody holds yet."""
    from database.manager_operation import get_all_stocks_from_db
    out = set()
    for s in (get_all_stocks_from_db() or {}).values():
        t = normalize_ticker((s or {}).get("ticker"))
        if t:
            out.add(t)
    return out


def main():
    initialize_firebase()

    if not traded_today():
        log.info("skipping: no settled session for today")
        return 0

    purchases = _open_purchases()

    # Cache the whole catalog -- a price the user has not bought yet still drives
    # the buy page and the weights the optimizer starts from.
    tickers = _catalog_tickers()
    tickers |= {normalize_ticker(p.get("ticker")) for p in purchases.values()}
    tickers.discard("")
    if not tickers:
        log.info("no tickers to price; nothing to do")
        return 0

    prices = get_prices(sorted(tickers))
    log.info("fetched %d/%d prices", len(prices), len(tickers))

    # get_prices falls back to last night's cache so a page never shows a blank
    # number. That is right for a render and wrong here: re-stamping a stale
    # close with today's date freezes it while looking current, and auto_sell
    # would trade against a price that is not real.
    stale, day = prices_are_stale(sorted(tickers))
    if stale:
        log.warning("dropping %d stale price(s) from %s: %s",
                    len(stale), day or "cache", ", ".join(stale))
        prices = {t: p for t, p in prices.items() if t not in stale}

    if not prices:
        log.error("no live prices returned -- aborting before writing anything")
        return 1

    log.info("cached %d prices", cache_prices(prices))

    if not purchases:
        log.info("no open purchases; prices cached, nothing to sell or snapshot")
        return 0

    log.info("auto-sold %d", auto_sell(purchases, prices))
    # After auto-sell: a target hit today should close the position rather than
    # be rebalanced into. Before the snapshot, so the snapshot reflects the
    # portfolio the user actually ends the day holding.
    log.info("rebalances executed %d", execute_rebalances(prices))
    # Re-read: auto_sell and the rebalances just changed which purchases are open.
    log.info("snapshotted %d users", snapshot(_open_purchases(), prices))
    return 0


if __name__ == "__main__":
    sys.exit(main())

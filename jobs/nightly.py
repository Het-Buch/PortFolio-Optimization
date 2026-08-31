"""Nightly cron: auto-sell on target, snapshot values, cache closes."""

import logging
import os
import sys
from datetime import datetime, timezone

from firebase_admin import db

from database.connection import initialize_firebase
from database.curd import sell_stock
from services.stock_services import get_prices, normalize_ticker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nightly")


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


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


def main():
    initialize_firebase()

    purchases = _open_purchases()
    if not purchases:
        log.info("no open purchases; nothing to do")
        return 0

    tickers = {normalize_ticker(p.get("ticker")) for p in purchases.values()}
    tickers.discard("")
    prices = get_prices(sorted(tickers))
    log.info("fetched %d/%d prices", len(prices), len(tickers))

    if not prices:
        log.error("no prices returned -- aborting before writing anything")
        return 1

    log.info("auto-sold %d", auto_sell(purchases, prices))
    # Re-read: auto_sell just changed which purchases are open.
    log.info("snapshotted %d users", snapshot(_open_purchases(), prices))
    log.info("cached %d prices", cache_prices(prices))
    return 0


if __name__ == "__main__":
    sys.exit(main())

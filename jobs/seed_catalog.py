"""One-shot: seed the stock catalog from the ticker CSV. Run: python -m jobs.seed_catalog"""

import sys
import time

import pandas as pd

from database.connection import initialize_firebase
from database.manager_operation import add_stock_to_db, get_all_stocks_from_db
from services.stock_services import get_history, get_profile, normalize_ticker

CSV = "ml/top 80 compines with ticker.csv"
THROTTLE = 0.4  # .info is rate-limited; pace it or the tail of the list fails


def main():
    initialize_firebase()

    tickers = [normalize_ticker(t) for t in pd.read_csv(CSV)["Ticker"].dropna()]
    tickers = sorted({t for t in tickers if t})
    print(f"{len(tickers)} tickers in {CSV}")

    # One batched download tells us which symbols still trade -- no .info needed.
    live = set(get_history(tickers, period="5d").columns)
    dead = [t for t in tickers if t not in live]
    print(f"{len(live)} resolved, {len(dead)} dead/renamed: {dead}")

    existing = {str(s.get("ticker", "")).upper()
                for s in (get_all_stocks_from_db() or {}).values()}

    added = failed = 0
    for i, ticker in enumerate(sorted(live), 1):
        if ticker in existing:
            continue
        profile = get_profile(ticker)
        name = profile["name"] if profile["resolved"] else ticker.replace(".NS", "")
        if add_stock_to_db(name, ticker, 0.0, profile["sector"]):
            added += 1
            print(f"  [{i}/{len(live)}] {name} | {profile['sector']}")
        else:
            failed += 1
        time.sleep(THROTTLE)

    print(f"\nadded {added}, failed {failed}, skipped {len(existing)} existing")
    return 0


if __name__ == "__main__":
    sys.exit(main())

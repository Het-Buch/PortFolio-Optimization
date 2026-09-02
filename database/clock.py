"""One clock for every stored timestamp: IST.

`datetime.now()` reads the *server's* local zone. That is IST on a local
machine and UTC on Streamlit Cloud, so the same purchase was stamped 21:59
locally and 16:29 deployed. This app is NSE-only -- a trading day is an IST
calendar day -- so IST is the correct zone everywhere, not a display choice.

Session expiry deliberately stays on UTC (database/session.py): that is
duration arithmetic, not a wall-clock date a user reads.
"""

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

FORMAT = "%Y-%m-%d %H:%M:%S"


def now():
    """Timezone-aware current IST time."""
    return datetime.now(IST)


def stamp():
    """The string form written to Firebase. Same format as before, right zone."""
    return now().strftime(FORMAT)


def today():
    """IST calendar date -- an NSE trading day."""
    return now().strftime("%Y-%m-%d")


def year2():
    """Two-digit IST year, used by the ID counters."""
    return now().year % 100

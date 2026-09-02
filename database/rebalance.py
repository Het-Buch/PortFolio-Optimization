"""Scheduled rebalances: a user accepts a plan, the nightly job executes it.

The plan stores **share counts**, not weights. Weights would have to be
re-derived at execution time against different prices, silently turning the
thing the user agreed to into something else. Share counts are exactly what was
shown and accepted; only the price they transact at moves.
"""
from database import clock

from firebase_admin import db

from database.connection import initialize_firebase

try:  # real init happens in main.py; never fail at import
    initialize_firebase()
except Exception:
    pass

# Bump when the wording changes -- an accepted plan records the version it was
# accepted under, so consent is auditable rather than assumed.
TERMS_VERSION = "1.0"

PENDING = "pending"
CANCELLED = "cancelled"
EXECUTED = "executed"
FAILED = "failed"


def _plan_id():
    n = db.reference("counters/rebalances").transaction(lambda cur: (cur or 0) + 1)
    return f"{clock.year2()}r{int(n):07d}"


def create_plan(user_id, orders, algorithm=""):
    """Accept a plan. Supersedes any pending one -- two live plans for the same
    portfolio would execute against each other."""
    actionable = [o for o in (orders or []) if int(o.get("delta", 0) or 0) != 0]
    if not actionable:
        return None

    for existing in (pending_for(user_id) or []):
        cancel(existing["plan_id"], user_id, reason="superseded")

    plan_id = _plan_id()
    now = clock.stamp()
    db.reference(f"rebalance_plans/{plan_id}").set({
        "plan_id": plan_id,
        "user_id": user_id,
        "status": PENDING,
        "created_at": now,
        "accepted_at": now,
        "terms_version": TERMS_VERSION,
        "algorithm": algorithm,
        "orders": [{
            "ticker": str(o.get("ticker", "")).strip().upper(),
            "company": o.get("company", ""),
            "stock_id": o.get("stock_id", ""),
            "held_at_plan": int(o.get("held", 0) or 0),
            "target": int(o.get("target", 0) or 0),
            "delta": int(o.get("delta", 0) or 0),
            "action": o.get("action", "HOLD"),
            "price_at_plan": float(o.get("price", 0) or 0),
        } for o in actionable],
    })
    return plan_id


def pending_for(user_id):
    """Every pending plan for one user. Indexed; falls back to a scan."""
    ref = db.reference("rebalance_plans")
    try:
        rows = ref.order_by_child("user_id").equal_to(user_id).get() or {}
    except Exception as e:
        print(f"rebalance_plans: unindexed scan ({e}); add .indexOn user_id")
        rows = {k: v for k, v in (ref.get() or {}).items()
                if (v or {}).get("user_id") == user_id}
    return [v for v in rows.values() if (v or {}).get("status") == PENDING]


def all_pending():
    """Every pending plan, for the scheduled job."""
    ref = db.reference("rebalance_plans")
    try:
        rows = ref.order_by_child("status").equal_to(PENDING).get() or {}
    except Exception as e:
        print(f"rebalance_plans: unindexed scan ({e}); add .indexOn status")
        rows = {k: v for k, v in (ref.get() or {}).items()
                if (v or {}).get("status") == PENDING}
    return list(rows.values())


def cancel(plan_id, user_id, reason="user"):
    """Cancel a pending plan. Scoped to its owner so an id alone is not enough."""
    ref = db.reference(f"rebalance_plans/{plan_id}")
    plan = ref.get()
    if not plan or plan.get("user_id") != user_id:
        return False
    if plan.get("status") != PENDING:
        return False
    ref.update({
        "status": CANCELLED,
        "cancelled_at": clock.stamp(),
        "cancelled_reason": reason,
    })
    return True


def claim(plan_id):
    """Move pending -> executing exactly once, so a retried or overlapping job
    cannot execute the same plan twice. Returns True only if *this* caller made
    the transition.

    The final value cannot be the test: a second caller sees "executing"
    already, returns it unchanged, and would read that back as success --
    which is precisely a double execution.
    """
    ref = db.reference(f"rebalance_plans/{plan_id}/status")
    won = {"ok": False}

    def _take(current):
        # Firebase may retry this callback, so decide fresh every invocation.
        won["ok"] = current == PENDING
        return "executing" if won["ok"] else current

    ref.transaction(_take)
    return won["ok"]


def finish(plan_id, status, detail=None):
    db.reference(f"rebalance_plans/{plan_id}").update({
        "status": status,
        "executed_at": clock.stamp(),
        "result": detail or {},
    })

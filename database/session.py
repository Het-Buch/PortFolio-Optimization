"""Server-side sessions. The cookie holds an opaque token and nothing else."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from firebase_admin import db

from database.connection import initialize_firebase

try:  # real init happens in main.py; never fail at import
    initialize_firebase()
except Exception:
    pass

TTL_MINUTES = 30
COOKIE_NAME = "pms_session"


def _hash(token):
    """Store only the hash, so a DB leak cannot be replayed as a login."""
    return hashlib.sha256(token.encode()).hexdigest()


def _now():
    return datetime.now(timezone.utc)


def create(user_id, is_manager=False):
    """Issue a token. Returns (token, expiry) -- the caller sets the cookie."""
    token = secrets.token_urlsafe(32)
    expires = _now() + timedelta(minutes=TTL_MINUTES)
    db.reference(f"sessions/{_hash(token)}").set({
        "user_id": user_id,
        "is_manager": bool(is_manager),
        "expires_at": expires.isoformat(),
        "created_at": _now().isoformat(),
    })
    return token, expires


def resolve(token):
    """Return (user_id, is_manager) for a live token, else (None, False)."""
    if not token:
        return None, False

    ref = db.reference(f"sessions/{_hash(token)}")
    row = ref.get()
    if not row:
        return None, False

    try:
        expired = datetime.fromisoformat(row["expires_at"]) <= _now()
    except Exception:
        expired = True

    if expired:
        ref.delete()
        return None, False

    return row.get("user_id"), bool(row.get("is_manager"))


def refresh(token):
    """Slide the expiry forward on activity."""
    if not token:
        return None
    ref = db.reference(f"sessions/{_hash(token)}")
    if not ref.get():
        return None
    expires = _now() + timedelta(minutes=TTL_MINUTES)
    ref.update({"expires_at": expires.isoformat()})
    return expires


def destroy(token):
    if token:
        db.reference(f"sessions/{_hash(token)}").delete()


def purge_expired():
    """Housekeeping for the nightly job."""
    rows = db.reference("sessions").get() or {}
    removed = 0
    for key, row in rows.items():
        try:
            alive = datetime.fromisoformat((row or {})["expires_at"]) > _now()
        except Exception:
            alive = False
        if not alive:
            db.reference(f"sessions/{key}").delete()
            removed += 1
    return removed


def _self_check():
    t = secrets.token_urlsafe(32)
    assert _hash(t) != t and len(_hash(t)) == 64
    assert _hash(t) == _hash(t)
    assert resolve(None) == (None, False)
    assert resolve("") == (None, False)
    print("session: OK (hashing only; DB paths need Firebase)")


if __name__ == "__main__":
    _self_check()

"""Identity resolution. Email/password and Google both land here."""

import os

from firebase_admin import db

from database.connection import initialize_firebase, _setting

try:  # real init happens in main.py; never fail at import
    initialize_firebase()
except Exception:
    pass


def _users():
    return db.reference("users").get() or {}


def user_id_for_email(email):
    """Find an existing user_id by email. Returns (user_id, blocked)."""
    target = str(email or "").strip().lower()
    if not target:
        return None, False

    for record in _users().values():
        personal = (record or {}).get("personal", {})
        if str(personal.get("email", "")).strip().lower() == target:
            return personal.get("user_id"), bool(personal.get("blocked", False))
    return None, False


def is_manager(email):
    """Manager access is an email allowlist in secrets, not a shared password."""
    raw = _setting("manager_emails") or _setting("manager_email") or ""
    allowed = {e.strip().lower() for e in str(raw).split(",") if e.strip()}
    return str(email or "").strip().lower() in allowed


def provision_google_user(email, name):
    """Create a minimal user record on first Google sign-in."""
    from database.register_user import generate_user_id
    from datetime import datetime

    user_id = generate_user_id()
    if not user_id:
        return None

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ref = db.reference("users").child(user_id)
    ref.child("personal").set({
        "user_id": user_id,
        "email": str(email).strip().lower(),
        "name": name or str(email).split("@")[0],
        "phone": "",
        "uid": f"google:{email}",
        "blocked": False,
        "provider": "google",
    })
    ref.child("login").set({
        "first_login_date": now, "last_login_date": now,
        "modified_on": now, "modified_by": user_id,
    })
    return user_id


def sign_in_with_google(email, name=""):
    """Resolve a Google identity to a user_id, provisioning if new."""
    user_id, blocked = user_id_for_email(email)
    if blocked:
        return None
    if user_id:
        from datetime import datetime
        db.reference("users").child(user_id).child("login").update(
            {"last_login_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        return user_id
    return provision_google_user(email, name)

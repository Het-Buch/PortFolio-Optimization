"""Firebase init. Creds: st.secrets -> FIREBASE_CREDENTIALS env -> local file. Raises on failure."""

import json
import os
import glob

import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv

# Explicit paths: bare load_dotenv() resolves against the caller's frame, which
# misses these depending on how the app is launched.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _env in (".env", "database/.env", "ml/.env"):
    load_dotenv(os.path.join(_ROOT, _env), override=False)


def _secrets():
    """st.secrets, or {} when Streamlit isn't running (CLI, Actions)."""
    try:
        import streamlit as st
        return st.secrets
    except Exception:
        return {}


def _setting(name, default=None):
    """Look up a config value in st.secrets first, then the environment."""
    sec = _secrets()
    try:
        if name in sec:
            return sec[name]
    except Exception:
        pass
    return os.getenv(name, default)


def _credentials():
    sec = _secrets()

    try:
        if "firebase" in sec:
            return credentials.Certificate(dict(sec["firebase"]))
    except Exception:
        pass

    raw = os.getenv("FIREBASE_CREDENTIALS")
    if raw:
        return credentials.Certificate(json.loads(raw))

    path = os.getenv("FIREBASE_CREDENTIALS_FILE")
    matches = [path] if path else sorted(glob.glob("*firebase-adminsdk*.json"))
    if matches and matches[0] and os.path.exists(matches[0]):
        return credentials.Certificate(matches[0])

    raise RuntimeError(
        "No Firebase credentials. Set st.secrets['firebase'] (Streamlit Cloud), "
        "FIREBASE_CREDENTIALS (Actions), or place the service-account JSON in the "
        "project root (local dev)."
    )


def initialize_firebase():
    """Idempotent. Safe to call from every module that needs the DB."""
    if firebase_admin._apps:
        return firebase_admin

    database_url = _setting("databaseURL")
    if not database_url:
        raise RuntimeError("databaseURL is not configured.")

    firebase_admin.initialize_app(_credentials(), {"databaseURL": database_url})
    return firebase_admin

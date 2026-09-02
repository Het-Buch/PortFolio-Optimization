"""Field validation shared by the forms.

Each check returns an error string or None, so a caller can collect every
problem and show them together instead of making the user fix one, submit,
and discover the next.
"""

import re

# Deliberately not RFC 5322: that regex is unreadable and still accepts things
# no mail server will. This rejects what users actually get wrong.
_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")
_NAME = re.compile(r"^[A-Za-z][A-Za-z .'-]*$")


def email(value):
    v = str(value or "").strip()
    if not v:
        return "Email is required."
    if " " in v:
        return "Email cannot contain spaces."
    if not _EMAIL.match(v):
        return "Enter a valid email address, like name@example.com."
    if len(v) > 254:
        return "That email is too long."
    local, _, domain = v.partition("@")
    if ".." in v or v.startswith(".") or local.endswith("."):
        return "That email has misplaced dots."
    if domain.split(".")[-1].isdigit():
        return "That email's domain looks invalid."
    return None


def name(value):
    v = str(value or "").strip()
    if not v:
        return "Name is required."
    if len(v) < 2:
        return "Name is too short."
    if len(v) > 60:
        return "Name is too long."
    if not _NAME.match(v):
        return "Name should contain letters only (spaces, ' and - are allowed)."
    return None


def phone(value):
    v = re.sub(r"\D", "", str(value or ""))
    if not v:
        return "Phone number is required."
    if len(v) != 10:
        return "Enter a 10-digit mobile number."
    if v[0] not in "6789":
        return "An Indian mobile number starts with 6, 7, 8 or 9."
    if len(set(v)) == 1:
        return "That doesn't look like a real number."
    return None


def password(value):
    v = str(value or "")
    if not v:
        return "Password is required."
    # Firebase itself rejects under 6; catch it here with a useful message
    # instead of surfacing a raw API error after a round trip.
    if len(v) < 8:
        return "Use at least 8 characters."
    if v.isdigit() or v.isalpha():
        return "Mix letters and numbers."
    if v.lower() in {"password", "12345678", "qwerty123", "password1"}:
        return "That password is too common."
    return None


def confirm(value, other):
    if not value:
        return "Please re-enter the password."
    if value != other:
        return "Passwords do not match."
    return None


def quantity(value, most=None):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return "Quantity must be a whole number."
    if n <= 0:
        return "Quantity must be at least 1."
    if most is not None and n > most:
        return f"You only hold {most}."
    return None


def money(value, field="Amount"):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return f"{field} must be a number."
    if v <= 0:
        return f"{field} must be greater than 0."
    return None


def first_error(*errors):
    """The first real problem, or None. Keeps call sites to one line."""
    for e in errors:
        if e:
            return e
    return None

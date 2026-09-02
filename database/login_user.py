import requests
import firebase_admin
from firebase_admin import auth ,db
from database import clock

from database.connection import initialize_firebase
from dotenv import load_dotenv
import os
# Ensure Firebase is initialized
try:  # real init happens in main.py; never fail at import
    initialize_firebase()
except Exception:
    pass
load_dotenv()
API_KEY = os.getenv("API_KEY")


def authenticate_user(email, password):
    """Returns (user_id, reason). reason is None on success, otherwise
    "credentials", "blocked" or "no_record" -- three states that used to be
    indistinguishable, so a valid password against an account missing its
    database row was reported as bad credentials."""
    try:
        # Check if the email exists in Firebase Authentication
        try:
            user_record = auth.get_user_by_email(email)  # Get user info by email
        except firebase_admin.auth.UserNotFoundError:
            return None, "credentials"  # Email not registered

        # Proceed with password authentication
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        response = requests.post(url, json=payload)
        data = response.json()

        if response.status_code == 200:

            # Check if the user ID exists in the Firebase Realtime Database
            uid = data.get("localId")
            users_ref = db.reference("users")
            try:
                # Indexed: server-side lookup instead of downloading every user.
                matches = users_ref.order_by_child("personal/uid").equal_to(uid).get() or {}
            except Exception as e:
                # No .indexOn rule yet -- correct but downloads the whole table.
                print(f"users: unindexed scan ({e}); add .indexOn personal/uid to the rules")
                matches = users_ref.get() or {}

            user_id = None
            blocked = False
            for user_data in matches.values():
                personal = (user_data or {}).get("personal", {})
                if personal.get("uid") == uid:
                    user_id = personal.get("user_id")
                    blocked = personal.get("blocked", False)
                    break
            if not user_id:
                # Password was correct but no users/ row exists -- a half-created
                # account. Saying "invalid credentials" here sends the user to
                # reset a password that was never the problem.
                return None, "no_record"
            if blocked:
                return None, "blocked"

            # Update login time
            login = {
                "last_login_date": clock.stamp()
            }
            users_ref.child(user_id).child("login").update(login)
            return user_id, None
        else:
            return None, "credentials"

    except Exception as e:
        print(f"Error authenticating user: {e}")
        return None, "credentials"
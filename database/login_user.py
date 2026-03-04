import requests
import firebase_admin
from firebase_admin import auth ,db
from datetime import datetime

from database.connection import initialize_firebase
from dotenv import load_dotenv
import os
# Ensure Firebase is initialized
initialize_firebase()
load_dotenv()
API_KEY = os.getenv("API_KEY")


def authenticate_user(email, password):
    try:
        # Check if the email exists in Firebase Authentication
        try:
            user_record = auth.get_user_by_email(email)  # Get user info by email
        except firebase_admin.auth.UserNotFoundError:
            return None  # Email not registered

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
            users = users_ref.get() or {}
            user_id = None
            blocked = False
            for key, user_data in users.items():
                personal = user_data.get("personal", {})
                if personal.get("uid") == uid:
                    user_id = personal.get("user_id")
                    blocked = personal.get("blocked", False)
                    break
            # If user not found or blocked
            if not user_id or blocked:
                return None
            # Update login time
            login = {
                "last_login_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            users_ref.child(user_id).child("login").update(login)
            return user_id
        else:
            return None  # Login failed

    except Exception as e:
        print(f"Error authenticating user: {e}")
        return None
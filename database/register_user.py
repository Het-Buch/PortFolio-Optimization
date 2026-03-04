import firebase_admin
from firebase_admin import auth, db
from datetime import datetime
import requests

# Initialize Firebase connection
from database.connection import initialize_firebase

initialize_firebase()

def generate_user_id():
    try:
        # Get the last two digits of the current year
        year_suffix = datetime.now().year % 100  # Example: 2024 → 24

        # Reference to the database path
        ref = db.reference("users")

        if not ref.get():
            ref.set({})

        # Fetch all users ordered by user_id
        users = ref.get()

        if users:
            last_user_id = max(users.keys())  
            last_number = int(last_user_id[3:])
        else:
            last_number = 0  # Start from 1 if no users exist

        # Generate new user ID
        new_number = last_number + 1
        user_id = f"{year_suffix}u{new_number:07d}"  # Format: 24u0000001

        return user_id

    except Exception as e:
        print(f"Error generating user ID: {e}")
        return None
    
def email_verification(email):
    try:
        # Reference to the database path
        ref = db.reference("users")

        # Fetch all users (Ordered by `user_id`)
        users = ref.get() or {}

        # Check if email already exists
        for user in users.values():
            personal_data = user.get("personal",{})
            if personal_data.get("email") == email:
                return "User already registered! Please Login"

        return None
    except Exception as e:
        print(f"Error verifying email: {e}")
        return None

def register_user(email,password,name,phone,country,state,city,zip_code):
    try:
        # Check if email already exists
        email_exists = email_verification(email)
        if email_exists:
            return email_exists

        # Generate unique user ID
        user_id = generate_user_id()
        if not user_id:
            return "Failed to generate User ID."
        
        # create Firebase Authentication user
        user = auth.create_user(
            email=email,
            password=password
        )

        # Store user data in Realtime Database
        personal = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "phone": phone,
            "uid": user.uid,
            "blocked": False,  
            # "verified": True,  # for now skipping the verification
        }
        address={
            "country": country,
            "state": state,
            "city": city,
            "zip_code": zip_code,
        }

        login={
            "first_login_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_login_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "modified_on": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "modified_by": user_id,
        }


        ref = db.reference("users")

        # Store data using `user_id` as the key
        ref.child(user_id).child("personal").set(personal)

        # Store address data using `user_id` as the key
        ref.child(user_id).child("address").set(address)

        ref.child(user_id).child("login").set(login)

        return f"User registered successfully! Your User ID is {user_id}."

    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    register_user(email,password,name,phone,country,state,city,zip_code)
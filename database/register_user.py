from firebase_admin import auth, db
from database import clock

# Initialize Firebase connection
from database.connection import initialize_firebase

try:  # real init happens in main.py; never fail at import
    initialize_firebase()
except Exception:
    pass

def generate_user_id():
    n = db.reference("counters/users").transaction(lambda cur: (cur or 0) + 1)
    return f"{clock.year2()}u{int(n):07d}"
    
def email_verification(email):
    try:
        ref = db.reference("users")
        try:
            # Indexed: server-side lookup instead of downloading every user.
            matches = ref.order_by_child("personal/email").equal_to(email).get() or {}
        except Exception as e:
            # No .indexOn rule yet -- correct but downloads the whole table.
            print(f"users: unindexed scan ({e}); add .indexOn personal/email to the rules")
            matches = {k: v for k, v in (ref.get() or {}).items()
                      if (v or {}).get("personal", {}).get("email") == email}

        return "User already registered! Please Login" if matches else None
    except Exception as e:
        print(f"Error verifying email: {e}")
        return None

def register_user(email,password,name,phone,country,state,city,zip_code):
    try:
        # Normalize once so the stored value always matches the indexed
        # lookup -- an unnormalized write here previously meant a login or a
        # Google-account link could silently miss if the user had typed any
        # uppercase letter in their email at registration.
        email = str(email or "").strip().lower()

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
            "first_login_date": clock.stamp(),
            "last_login_date": clock.stamp(),
            "modified_on": clock.stamp(),
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
import firebase_admin
from firebase_admin import credentials, db
import os
from dotenv import load_dotenv

load_dotenv()
def initialize_firebase():
    if not firebase_admin._apps:

        try:
            cred = credentials.Certificate("portfolio-optimization-dbf9c-firebase-adminsdk-fbsvc-0157b59df4.json")

            # Initialize the app with the Realtime Database URL
            firebase_admin.initialize_app(cred, {
                'databaseURL': os.getenv("databaseURL")
            })


            print("Firebase Admin SDK initialized.")

            return firebase_admin

        except Exception as e:
            print(f"Failed to Connect: {e}")


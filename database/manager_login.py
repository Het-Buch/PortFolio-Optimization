import os
from dotenv import load_dotenv
load_dotenv()
def authenticate_manager(email, password):

    if email== os.getenv("manager_email") and password==os.getenv("manager_password"):
        return "manager"
    else:
        return None
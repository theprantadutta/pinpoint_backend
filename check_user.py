"""Quick script to check user subscription status"""
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import SessionLocal
from app.models.user import User
from datetime import datetime

db = SessionLocal()

try:
    user = db.query(User).filter(User.email == "prantadutta1997@gmail.com").first()

    if user:
        print(f"User: {user.email}")
        print(f"ID: {user.id}")
        print(f"Firebase UID: {user.firebase_uid}")
        print(f"Subscription Tier: {user.subscription_tier}")
        print(f"Subscription Expires At: {user.subscription_expires_at}")
        print(f"Is Premium (computed): {user.is_premium}")
        print(f"Current Time: {datetime.utcnow()}")

        if user.subscription_expires_at:
            if datetime.utcnow() < user.subscription_expires_at:
                print(f"Status: ACTIVE (expires in {user.subscription_expires_at - datetime.utcnow()})")
            else:
                print(f"Status: EXPIRED (expired {datetime.utcnow() - user.subscription_expires_at} ago)")
        else:
            print("Status: No expiration date set")
    else:
        print("User not found")

finally:
    db.close()

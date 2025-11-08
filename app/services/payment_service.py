"""Payment and subscription service"""
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.device import Device
from app.models.subscription import SubscriptionEvent
from app.config import settings
from datetime import datetime, timedelta
from typing import Optional, Dict
import os


class PaymentService:
    """Service for handling payments and subscriptions"""

    def __init__(self, db: Session):
        self.db = db
        self.google_play_service = None

        # Initialize Google Play service if credentials exist
        if os.path.exists(settings.GOOGLE_PLAY_SERVICE_ACCOUNT_PATH):
            try:
                from google.oauth2 import service_account
                from googleapiclient.discovery import build

                credentials = service_account.Credentials.from_service_account_file(
                    settings.GOOGLE_PLAY_SERVICE_ACCOUNT_PATH,
                    scopes=['https://www.googleapis.com/auth/androidpublisher']
                )

                self.google_play_service = build(
                    'androidpublisher',
                    'v3',
                    credentials=credentials
                )
            except Exception as e:
                print(f"Warning: Could not initialize Google Play service: {e}")

    async def verify_google_play_purchase(
        self,
        user_id: str,
        purchase_token: str,
        product_id: str
    ) -> Dict:
        """
        Verify Google Play subscription purchase

        Args:
            user_id: User ID
            purchase_token: Purchase token from Google Play
            product_id: Product ID (e.g., 'pinpoint_premium_monthly')

        Returns:
            Dictionary with verification result
        """
        if not self.google_play_service:
            # For development: Mock verification
            return await self._mock_verify_purchase(user_id, product_id)

        try:
            # Verify with Google Play API
            subscription = self.google_play_service.purchases().subscriptions().get(
                packageName=settings.GOOGLE_PLAY_PACKAGE_NAME,
                subscriptionId=product_id,
                token=purchase_token
            ).execute()

            # Extract expiry time
            expiry_time_millis = int(subscription.get('expiryTimeMillis', 0))
            expiry_time = datetime.fromtimestamp(expiry_time_millis / 1000)

            is_active = expiry_time > datetime.utcnow()

            if is_active:
                # Update user's subscription
                user = self.db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {"success": False, "message": "User not found"}

                user.subscription_tier = 'premium'
                user.subscription_expires_at = expiry_time
                user.google_play_purchase_token = purchase_token

                # Log subscription event
                subscription_event = SubscriptionEvent(
                    user_id=user_id,
                    event_type='purchase',
                    purchase_token=purchase_token,
                    product_id=product_id,
                    platform='android',
                    expires_at=expiry_time,
                    raw_receipt=str(subscription)
                )

                self.db.add(subscription_event)
                self.db.commit()

                return {
                    "success": True,
                    "tier": "premium",
                    "expires_at": expiry_time,
                    "message": "Subscription verified successfully"
                }
            else:
                return {
                    "success": False,
                    "tier": "free",
                    "message": "Subscription has expired"
                }

        except Exception as e:
            return {
                "success": False,
                "tier": "free",
                "message": f"Verification failed: {str(e)}"
            }

    async def _mock_verify_purchase(
        self,
        user_id: str,
        product_id: str
    ) -> Dict:
        """
        Mock purchase verification for development

        This simulates a successful purchase without actual Google Play verification
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "message": "User not found"}

        # Determine subscription period based on product ID
        if 'monthly' in product_id:
            duration = timedelta(days=30)
        elif 'yearly' in product_id:
            duration = timedelta(days=365)
        elif 'lifetime' in product_id:
            duration = None  # No expiry
        else:
            duration = timedelta(days=30)

        expiry_time = datetime.utcnow() + duration if duration else None

        user.subscription_tier = 'premium'
        user.subscription_expires_at = expiry_time

        # Log subscription event
        subscription_event = SubscriptionEvent(
            user_id=user_id,
            event_type='purchase',
            product_id=product_id,
            platform='android',
            expires_at=expiry_time,
            raw_receipt='MOCK_PURCHASE_FOR_DEVELOPMENT'
        )

        self.db.add(subscription_event)
        self.db.commit()

        return {
            "success": True,
            "tier": "premium",
            "expires_at": expiry_time,
            "message": "Subscription verified successfully (DEV MODE)"
        }

    def get_subscription_status(self, user_id: str) -> Dict:
        """
        Get current subscription status for a user

        Args:
            user_id: User ID

        Returns:
            Dictionary with subscription status
        """
        user = self.db.query(User).filter(User.id == user_id).first()

        if not user:
            return {
                "is_premium": False,
                "tier": "free",
                "expires_at": None,
                "product_id": None
            }

        # Get latest subscription event
        latest_event = self.db.query(SubscriptionEvent).filter(
            SubscriptionEvent.user_id == user_id
        ).order_by(SubscriptionEvent.verified_at.desc()).first()

        return {
            "is_premium": user.is_premium,
            "tier": user.subscription_tier,
            "expires_at": user.subscription_expires_at,
            "product_id": latest_event.product_id if latest_event else None
        }

    async def verify_google_play_purchase_for_device(
        self,
        device_id: str,
        purchase_token: str,
        product_id: str
    ) -> Dict:
        """
        Verify Google Play purchase for a device (no user authentication)

        Args:
            device_id: Device ID
            purchase_token: Purchase token from Google Play
            product_id: Product ID (e.g., 'pinpoint_premium_monthly')

        Returns:
            Dictionary with verification result
        """
        if not self.google_play_service:
            # For development: Mock verification
            return await self._mock_verify_device_purchase(device_id, product_id)

        try:
            # Verify with Google Play API
            subscription = self.google_play_service.purchases().subscriptions().get(
                packageName=settings.GOOGLE_PLAY_PACKAGE_NAME,
                subscriptionId=product_id,
                token=purchase_token
            ).execute()

            # Extract expiry time
            expiry_time_millis = int(subscription.get('expiryTimeMillis', 0))
            expiry_time = datetime.fromtimestamp(expiry_time_millis / 1000)

            is_active = expiry_time > datetime.utcnow()

            if is_active:
                # Update device subscription
                device = self.db.query(Device).filter(Device.device_id == device_id).first()
                if not device:
                    device = Device(device_id=device_id)
                    self.db.add(device)

                device.subscription_tier = 'premium'
                device.subscription_product_id = product_id
                device.subscription_expires_at = expiry_time
                device.last_purchase_token = purchase_token
                device.purchase_verified_at = datetime.utcnow()

                self.db.commit()

                return {
                    "success": True,
                    "is_premium": True,
                    "tier": "premium",
                    "expires_at": expiry_time,
                    "message": "Subscription verified successfully"
                }
            else:
                return {
                    "success": False,
                    "is_premium": False,
                    "tier": "free",
                    "message": "Subscription has expired"
                }

        except Exception as e:
            return {
                "success": False,
                "is_premium": False,
                "tier": "free",
                "message": f"Verification failed: {str(e)}"
            }

    async def _mock_verify_device_purchase(
        self,
        device_id: str,
        product_id: str
    ) -> Dict:
        """
        Mock device purchase verification for development
        """
        device = self.db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            device = Device(device_id=device_id)
            self.db.add(device)

        # Determine subscription period based on product ID
        if 'monthly' in product_id:
            duration = timedelta(days=30)
        elif 'yearly' in product_id:
            duration = timedelta(days=365)
        elif 'lifetime' in product_id:
            duration = None  # No expiry
        else:
            duration = timedelta(days=30)

        expiry_time = datetime.utcnow() + duration if duration else None

        device.subscription_tier = 'premium'
        device.subscription_product_id = product_id
        device.subscription_expires_at = expiry_time
        device.purchase_verified_at = datetime.utcnow()

        self.db.commit()

        return {
            "success": True,
            "is_premium": True,
            "tier": "premium",
            "expires_at": expiry_time,
            "message": "Subscription verified successfully (DEV MODE)"
        }

"""Push notification service using Firebase Cloud Messaging"""
from sqlalchemy.orm import Session
from app.models.notification import FCMToken
from app.config import settings
from typing import Optional, Dict
import os


class NotificationService:
    """Service for handling push notifications"""

    def __init__(self, db: Session):
        self.db = db
        self.firebase_app = None

        # Initialize Firebase if credentials exist
        if os.path.exists(settings.FCM_CREDENTIALS_PATH):
            try:
                import firebase_admin
                from firebase_admin import credentials

                if not firebase_admin._apps:
                    cred = credentials.Certificate(settings.FCM_CREDENTIALS_PATH)
                    self.firebase_app = firebase_admin.initialize_app(cred)
                    print(f"✅ Firebase Admin SDK initialized successfully")
                else:
                    self.firebase_app = firebase_admin.get_app()
                    print(f"✅ Using existing Firebase Admin SDK instance")
            except Exception as e:
                print(f"❌ Error: Could not initialize Firebase Admin SDK: {e}")
                raise RuntimeError(f"Firebase initialization failed: {e}")
        else:
            print(f"❌ Warning: Firebase credentials not found at {settings.FCM_CREDENTIALS_PATH}")
            print(f"⚠️  Push notifications and Firebase authentication will not work!")
            raise FileNotFoundError(
                f"Firebase Admin SDK credentials file not found: {settings.FCM_CREDENTIALS_PATH}\n"
                f"Please download credentials from Firebase Console and place at the specified path.\n"
                f"See CREDENTIALS_SETUP_GUIDE.md for instructions."
            )

    async def register_fcm_token(
        self,
        user_id: str,
        fcm_token: str,
        device_id: str,
        platform: str
    ) -> Dict:
        """
        Register or update FCM token for a user's device

        Args:
            user_id: User ID
            fcm_token: Firebase Cloud Messaging token
            device_id: Unique device identifier
            platform: Platform ('android', 'ios', 'web')

        Returns:
            Result dictionary
        """
        # Check if token already exists for this device
        existing_token = self.db.query(FCMToken).filter(
            FCMToken.user_id == user_id,
            FCMToken.device_id == device_id
        ).first()

        if existing_token:
            # Update existing token
            existing_token.fcm_token = fcm_token
            existing_token.platform = platform
        else:
            # Create new token record
            new_token = FCMToken(
                user_id=user_id,
                device_id=device_id,
                fcm_token=fcm_token,
                platform=platform
            )
            self.db.add(new_token)

        self.db.commit()

        return {
            "success": True,
            "message": "FCM token registered successfully"
        }

    async def remove_fcm_token(
        self,
        user_id: str,
        device_id: str
    ) -> Dict:
        """
        Remove FCM token for a device

        Args:
            user_id: User ID
            device_id: Device identifier

        Returns:
            Result dictionary
        """
        deleted_count = self.db.query(FCMToken).filter(
            FCMToken.user_id == user_id,
            FCMToken.device_id == device_id
        ).delete()

        self.db.commit()

        return {
            "success": True,
            "message": f"Removed {deleted_count} token(s)"
        }

    async def send_notification(
        self,
        fcm_token: str,
        title: str,
        body: str,
        data: Optional[Dict] = None
    ) -> Dict:
        """
        Send push notification to a specific device

        Args:
            fcm_token: FCM token
            title: Notification title
            body: Notification body
            data: Optional data payload

        Returns:
            Result with message ID if successful
        """
        if not self.firebase_app:
            # Mock notification for development
            return {
                "success": True,
                "message_id": "MOCK_MESSAGE_ID",
                "message": "Notification sent (DEV MODE)"
            }

        try:
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data or {},
                token=fcm_token
            )

            response = messaging.send(message)

            return {
                "success": True,
                "message_id": response,
                "message": "Notification sent successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to send notification: {str(e)}"
            }

    async def send_notification_to_user(
        self,
        user_id: str,
        title: str,
        body: str,
        data: Optional[Dict] = None
    ) -> Dict:
        """
        Send notification to all devices of a user

        Args:
            user_id: User ID
            title: Notification title
            body: Notification body
            data: Optional data payload

        Returns:
            Result with count of notifications sent
        """
        # Get all FCM tokens for the user
        tokens = self.db.query(FCMToken).filter(
            FCMToken.user_id == user_id
        ).all()

        if not tokens:
            return {
                "success": False,
                "message": "No FCM tokens found for user"
            }

        sent_count = 0
        failed_count = 0

        for token_record in tokens:
            result = await self.send_notification(
                fcm_token=token_record.fcm_token,
                title=title,
                body=body,
                data=data
            )

            if result["success"]:
                sent_count += 1
            else:
                failed_count += 1

        return {
            "success": True,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "message": f"Sent {sent_count} notifications, {failed_count} failed"
        }

    async def send_sync_notification(
        self,
        user_id: str,
        notes_count: int
    ) -> Dict:
        """
        Send a notification when notes have been synced

        Args:
            user_id: User ID
            notes_count: Number of notes synced

        Returns:
            Result dictionary
        """
        return await self.send_notification_to_user(
            user_id=user_id,
            title="Pinpoint",
            body=f"Synced {notes_count} note(s) across your devices",
            data={"type": "sync_complete", "notes_count": str(notes_count)}
        )

"""Push notification endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.notification import (
    FCMTokenRegister,
    PushNotificationSend,
    NotificationResponse
)
from app.services.notification_service import NotificationService
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/register", response_model=NotificationResponse)
async def register_fcm_token(
    token_data: FCMTokenRegister,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Register Firebase Cloud Messaging token for push notifications

    - **fcm_token**: FCM token from device
    - **device_id**: Unique device identifier
    - **platform**: Platform ('android', 'ios', 'web')
    """
    notification_service = NotificationService(db)

    result = await notification_service.register_fcm_token(
        user_id=str(current_user.id),
        fcm_token=token_data.fcm_token,
        device_id=token_data.device_id,
        platform=token_data.platform
    )

    return result


@router.delete("/token/{device_id}", response_model=NotificationResponse)
async def remove_fcm_token(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove FCM token for a device

    - **device_id**: Device identifier to remove
    """
    notification_service = NotificationService(db)

    result = await notification_service.remove_fcm_token(
        user_id=str(current_user.id),
        device_id=device_id
    )

    return result


@router.post("/send", response_model=NotificationResponse)
async def send_notification(
    notification_data: PushNotificationSend,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send push notification to all user's devices

    - **title**: Notification title
    - **body**: Notification body
    - **data**: Optional data payload
    """
    notification_service = NotificationService(db)

    result = await notification_service.send_notification_to_user(
        user_id=str(current_user.id),
        title=notification_data.title,
        body=notification_data.body,
        data=notification_data.data
    )

    return result


@router.post("/test")
async def test_notification(db: Session = Depends(get_db)):
    """
    Test endpoint to send a notification (no authentication required)

    This is for development/testing only. Returns Firebase initialization status.
    """
    notification_service = NotificationService(db)

    # Check if Firebase is initialized
    try:
        import firebase_admin
        from firebase_admin import messaging

        # Try to send a test message to a test token
        test_message = messaging.Message(
            notification=messaging.Notification(
                title="🎉 Backend Test Notification",
                body="Your Pinpoint backend is working! Firebase is connected."
            ),
            topic="test"  # This won't actually send, just validates Firebase is working
        )

        return {
            "success": True,
            "message": "Firebase is initialized and ready to send notifications!",
            "firebase_initialized": True,
            "test_message": {
                "title": "🎉 Backend Test Notification",
                "body": "Your Pinpoint backend is working! Firebase is connected."
            }
        }
    except ImportError:
        return {
            "success": False,
            "message": "Firebase Admin SDK not installed. Run: pip install firebase-admin",
            "firebase_initialized": False
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Firebase initialization error: {str(e)}",
            "firebase_initialized": False,
            "hint": "Make sure firebase-admin-sdk.json exists and is valid"
        }

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

"""Notification schemas"""
from pydantic import BaseModel
from typing import Optional, Dict, Any


class FCMTokenRegister(BaseModel):
    """Schema for registering FCM token"""
    fcm_token: str
    device_id: str
    platform: str  # 'android', 'ios', 'web'


class PushNotificationSend(BaseModel):
    """Schema for sending push notification"""
    title: str
    body: str
    data: Optional[Dict[str, Any]] = None


class NotificationResponse(BaseModel):
    """Schema for notification response"""
    success: bool
    message: str
    message_id: Optional[str] = None

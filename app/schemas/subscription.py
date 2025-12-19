"""Subscription schemas"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class GooglePlayPurchaseVerify(BaseModel):
    """Schema for Google Play purchase verification"""
    purchase_token: str
    product_id: str  # e.g., 'pinpoint_premium_monthly'


class DeviceBasedPurchaseVerify(BaseModel):
    """
    Schema for device-based purchase verification (no authentication required)

    Optionally accepts user_id to sync the subscription with the user's account
    when they are authenticated.
    """
    device_id: str
    purchase_token: str
    product_id: str
    user_id: Optional[str] = None  # Optional: sync subscription to user record if authenticated


class SubscriptionStatusResponse(BaseModel):
    """
    Schema for subscription status response

    Includes both 'tier' and 'subscription_type' for frontend compatibility.
    """
    is_premium: bool
    tier: str
    expires_at: Optional[datetime] = None
    product_id: Optional[str] = None
    is_in_grace_period: bool = False
    grace_period_ends_at: Optional[datetime] = None
    subscription_status: Optional[str] = None  # 'active', 'active_lifetime', 'grace_period', 'expired', 'free'
    subscription_type: Optional[str] = None  # Alias for frontend compatibility ('monthly', 'yearly', 'lifetime')


class PurchaseVerificationResponse(BaseModel):
    """Schema for purchase verification response"""
    success: bool
    is_premium: bool = False  # Whether the device/user now has premium access
    tier: str
    expires_at: Optional[datetime] = None
    is_in_grace_period: bool = False
    message: str

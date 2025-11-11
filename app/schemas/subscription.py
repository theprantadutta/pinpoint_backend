"""Subscription schemas"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class GooglePlayPurchaseVerify(BaseModel):
    """Schema for Google Play purchase verification"""
    purchase_token: str
    product_id: str  # e.g., 'pinpoint_premium_monthly'


class DeviceBasedPurchaseVerify(BaseModel):
    """Schema for device-based purchase verification (no authentication)"""
    device_id: str
    purchase_token: str
    product_id: str


class SubscriptionStatusResponse(BaseModel):
    """Schema for subscription status response"""
    is_premium: bool
    tier: str
    expires_at: Optional[datetime] = None
    product_id: Optional[str] = None
    is_in_grace_period: bool = False
    grace_period_ends_at: Optional[datetime] = None
    subscription_status: Optional[str] = None  # 'active', 'trial', 'grace_period', 'expired'


class PurchaseVerificationResponse(BaseModel):
    """Schema for purchase verification response"""
    success: bool
    tier: str
    expires_at: Optional[datetime] = None
    is_in_grace_period: bool = False
    message: str

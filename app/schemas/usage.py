"""Usage tracking and rate limiting schemas"""
from pydantic import BaseModel
from typing import Optional


class UsageLimitInfo(BaseModel):
    """Information about a specific usage limit"""
    current: int  # Current usage count
    limit: int  # Limit (-1 for unlimited)
    unlimited: bool  # True if premium user
    remaining: int  # Remaining before limit (-1 for unlimited)
    resets_at: Optional[str] = None  # ISO timestamp for monthly limits


class UsageStatsResponse(BaseModel):
    """Complete usage statistics for a user"""
    is_premium: bool
    subscription_tier: str  # 'free', 'premium', 'lifetime'
    synced_notes: UsageLimitInfo
    ocr_scans: UsageLimitInfo
    exports: UsageLimitInfo
    last_updated: str  # ISO timestamp


class ReconcileUsageRequest(BaseModel):
    """Request to reconcile usage counts"""
    user_id: Optional[str] = None  # Optional, defaults to current user


class ReconcileUsageResponse(BaseModel):
    """Response after reconciling usage"""
    success: bool
    message: str
    old_count: int
    new_count: int
    reconciled: bool


class IncrementUsageResponse(BaseModel):
    """Response after incrementing a usage counter"""
    success: bool
    message: str
    current: int  # New total after increment
    limit: int  # Limit (-1 for unlimited)
    remaining: int  # Remaining after increment (-1 for unlimited)

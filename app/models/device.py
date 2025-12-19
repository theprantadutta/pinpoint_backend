"""Device model for device-based subscriptions"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timedelta
from typing import Optional
import uuid
from app.database import Base
from app.config import settings


class Device(Base):
    """
    Device-based subscription tracking

    No user authentication required - tracks premium status by device ID
    """

    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id = Column(String(255), unique=True, nullable=False, index=True)

    # Subscription info
    subscription_tier = Column(String(50), default="free", nullable=False)
    subscription_product_id = Column(String(100), nullable=True)
    subscription_expires_at = Column(DateTime, nullable=True)

    # Grace period support (when payment fails, user keeps access for a few days)
    grace_period_ends_at = Column(DateTime, nullable=True)

    # Purchase tracking
    last_purchase_token = Column(String(500), nullable=True)
    purchase_verified_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def is_in_grace_period(self) -> bool:
        """Check if device is in grace period (payment failed but still has access)"""
        if self.grace_period_ends_at:
            return self.grace_period_ends_at > datetime.utcnow()
        return False

    @property
    def is_premium(self) -> bool:
        """Check if device has active premium subscription (includes grace period)"""
        # If in grace period, still consider premium
        if self.is_in_grace_period():
            return True

        if self.subscription_tier == "free":
            return False

        # Lifetime subscriptions don't expire
        if self.subscription_product_id and "lifetime" in self.subscription_product_id:
            return True

        # Check if subscription hasn't expired
        if self.subscription_expires_at:
            return self.subscription_expires_at > datetime.utcnow()

        return False

    def get_subscription_status(self) -> str:
        """
        Get detailed subscription status

        Returns:
            'active_lifetime' - Active lifetime subscription
            'active' - Active subscription (not expired)
            'grace_period' - Subscription expired but in grace period
            'expired' - Subscription expired
            'free' - No subscription
        """
        if self.subscription_tier == "free" and not self.is_in_grace_period():
            return "free"

        if self.subscription_product_id and "lifetime" in self.subscription_product_id:
            return "active_lifetime"

        if self.is_in_grace_period():
            return "grace_period"

        if self.subscription_expires_at and self.subscription_expires_at > datetime.utcnow():
            return "active"

        return "expired"

    def start_grace_period(self, days: Optional[int] = None) -> None:
        """
        Start grace period for this device

        Args:
            days: Number of days for grace period (defaults to settings.GRACE_PERIOD_DAYS)
        """
        grace_days = days if days is not None else getattr(settings, 'GRACE_PERIOD_DAYS', 3)
        self.grace_period_ends_at = datetime.utcnow() + timedelta(days=grace_days)

    def clear_grace_period(self) -> None:
        """Clear grace period (called when payment succeeds or subscription confirmed active)"""
        self.grace_period_ends_at = None

    def __repr__(self):
        return f"<Device(id={self.id}, device_id={self.device_id}, tier={self.subscription_tier})>"

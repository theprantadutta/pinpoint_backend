"""Device model for device-based subscriptions"""
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.database import Base


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

    # Purchase tracking
    last_purchase_token = Column(String(500), nullable=True)
    purchase_verified_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def is_premium(self) -> bool:
        """Check if device has active premium subscription"""
        if self.subscription_tier == "free":
            return False

        # Lifetime subscriptions don't expire
        if self.subscription_product_id and "lifetime" in self.subscription_product_id:
            return True

        # Check if subscription hasn't expired
        if self.subscription_expires_at:
            return self.subscription_expires_at > datetime.utcnow()

        return False

    def __repr__(self):
        return f"<Device(id={self.id}, device_id={self.device_id}, tier={self.subscription_tier})>"

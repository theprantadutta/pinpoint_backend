"""Subscription and payment models"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


class SubscriptionEvent(Base):
    """Track subscription purchases, renewals, and cancellations"""

    __tablename__ = "subscription_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Event type: 'purchase', 'renewal', 'cancellation', 'refund'
    event_type = Column(String(50), nullable=False)

    # Google Play purchase details
    purchase_token = Column(String(500), nullable=True)
    product_id = Column(String(100), nullable=True)  # e.g., 'pinpoint_premium_monthly'
    platform = Column(String(20), nullable=False)  # 'android', 'ios', 'web'

    # Timestamps
    verified_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)

    # Raw receipt data (for debugging)
    raw_receipt = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="subscription_events")

    def __repr__(self):
        return f"<SubscriptionEvent(id={self.id}, user_id={self.user_id}, type={self.event_type})>"

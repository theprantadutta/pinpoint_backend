"""Notification models"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


class FCMToken(Base):
    """Firebase Cloud Messaging tokens for push notifications"""

    __tablename__ = "fcm_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(255), nullable=False)

    fcm_token = Column(String(500), nullable=False)
    platform = Column(String(20), nullable=False)  # 'android', 'ios', 'web'

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="fcm_tokens")

    def __repr__(self):
        return f"<FCMToken(id={self.id}, user_id={self.user_id}, platform={self.platform})>"

"""Reminder model for backend-scheduled notifications"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base


class Reminder(Base):
    """
    Reminder model for backend-controlled notification scheduling

    Stores reminder times unencrypted to enable Celery-based scheduling.
    Sends FCM push notifications to all user devices at scheduled time.
    """

    __tablename__ = "reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Note reference (UUID from client-side note)
    note_uuid = Column(String(255), nullable=False, index=True)

    # Reminder details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    reminder_time = Column(DateTime, nullable=False, index=True)

    # Status tracking
    is_triggered = Column(Boolean, default=False, nullable=False, index=True)
    triggered_at = Column(DateTime, nullable=True)

    # Celery task tracking
    celery_task_id = Column(String(255), nullable=True)  # Celery task ID for cancellation

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="reminders")

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('ix_reminders_user_pending', 'user_id', 'is_triggered', 'reminder_time'),
        Index('ix_reminders_due', 'is_triggered', 'reminder_time'),
    )

    def is_due(self) -> bool:
        """Check if reminder is due to be triggered"""
        if self.is_triggered:
            return False
        return datetime.utcnow() >= self.reminder_time

    def is_future(self) -> bool:
        """Check if reminder is scheduled for the future"""
        if self.is_triggered:
            return False
        return datetime.utcnow() < self.reminder_time

    def mark_triggered(self):
        """Mark reminder as triggered"""
        self.is_triggered = True
        self.triggered_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def __repr__(self):
        return f"<Reminder(id={self.id}, user_id={self.user_id}, title='{self.title}', time={self.reminder_time}, triggered={self.is_triggered})>"

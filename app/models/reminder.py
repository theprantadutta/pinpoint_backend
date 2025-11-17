"""Reminder model for backend-scheduled notifications"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Index, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
import uuid
from app.database import Base


class RecurrenceType(str, Enum):
    """Types of reminder recurrence"""
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RecurrenceEndType(str, Enum):
    """How recurring reminders end"""
    NEVER = "never"
    AFTER_OCCURRENCES = "after_occurrences"
    ON_DATE = "on_date"


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

    # Reminder details (title is for internal organization, notification_title is shown to user)
    title = Column(String(500), nullable=False)  # Note title for app organization
    notification_title = Column(String(500), nullable=False)  # Title shown in push notification
    notification_content = Column(Text, nullable=True)  # Content shown in notification body
    description = Column(Text, nullable=True)  # Deprecated, use notification_content
    reminder_time = Column(DateTime, nullable=False, index=True)

    # Recurrence settings
    recurrence_type = Column(String(20), nullable=False, default="once", index=True)
    recurrence_interval = Column(Integer, nullable=False, default=1)  # Every X hours/days/weeks/months/years
    recurrence_end_type = Column(String(20), nullable=False, default="never")
    recurrence_end_value = Column(String(100), nullable=True)  # Number or ISO date string

    # Series tracking for recurring reminders
    parent_reminder_id = Column(UUID(as_uuid=True), ForeignKey("reminders.id", ondelete="CASCADE"), nullable=True, index=True)
    occurrence_number = Column(Integer, nullable=False, default=1)  # Which occurrence (1, 2, 3...)
    series_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Groups all occurrences

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
    parent = relationship("Reminder", remote_side=[id], backref="occurrences")

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

    def is_recurring(self) -> bool:
        """Check if reminder is part of a recurring series"""
        return self.recurrence_type != "once"

    def is_series_parent(self) -> bool:
        """Check if this is the parent of a recurring series"""
        return self.is_recurring() and self.parent_reminder_id is None

    def __repr__(self):
        return f"<Reminder(id={self.id}, user_id={self.user_id}, title='{self.title}', notification_title='{self.notification_title}', time={self.reminder_time}, recurrence={self.recurrence_type}, triggered={self.is_triggered})>"

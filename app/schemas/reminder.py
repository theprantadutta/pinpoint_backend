"""Reminder API schemas"""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from enum import Enum


class RecurrenceTypeEnum(str, Enum):
    """Types of reminder recurrence"""
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class RecurrenceEndTypeEnum(str, Enum):
    """How recurring reminders end"""
    NEVER = "never"
    AFTER_OCCURRENCES = "after_occurrences"
    ON_DATE = "on_date"


class ReminderCreate(BaseModel):
    """Schema for creating a new reminder"""
    note_uuid: str = Field(..., description="UUID of the associated note from client")
    title: str = Field(..., max_length=500, description="Note title (for app organization)")
    notification_title: str = Field(..., max_length=500, description="Title shown in push notification")
    notification_content: Optional[str] = Field(None, description="Content shown in notification body")
    reminder_time: datetime = Field(..., description="When to send the reminder (UTC)")

    # Recurrence settings
    recurrence_type: RecurrenceTypeEnum = Field(default=RecurrenceTypeEnum.ONCE, description="Type of recurrence")
    recurrence_interval: int = Field(default=1, ge=1, le=100, description="Interval for recurrence (e.g., every 2 days)")
    recurrence_end_type: RecurrenceEndTypeEnum = Field(default=RecurrenceEndTypeEnum.NEVER, description="How the recurrence ends")
    recurrence_end_value: Optional[str] = Field(None, description="Number of occurrences or ISO date string")

    @field_validator('reminder_time')
    @classmethod
    def validate_future_time(cls, v: datetime) -> datetime:
        """Ensure reminder time is in the future"""
        if v <= datetime.utcnow():
            raise ValueError('Reminder time must be in the future')
        return v

    @field_validator('recurrence_end_value')
    @classmethod
    def validate_end_value(cls, v: Optional[str], info) -> Optional[str]:
        """Validate recurrence end value based on end type"""
        if v is None:
            return v

        # Get the recurrence_end_type from the data
        data = info.data
        end_type = data.get('recurrence_end_type')

        if end_type == RecurrenceEndTypeEnum.AFTER_OCCURRENCES:
            # Should be a number
            try:
                num = int(v)
                if num <= 0:
                    raise ValueError('Number of occurrences must be positive')
            except ValueError:
                raise ValueError('recurrence_end_value must be a positive integer for AFTER_OCCURRENCES')
        elif end_type == RecurrenceEndTypeEnum.ON_DATE:
            # Should be a valid ISO date
            try:
                datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError('recurrence_end_value must be a valid ISO date string for ON_DATE')

        return v


class ReminderUpdate(BaseModel):
    """Schema for updating an existing reminder"""
    title: Optional[str] = Field(None, max_length=500, description="Note title")
    notification_title: Optional[str] = Field(None, max_length=500, description="Notification title")
    notification_content: Optional[str] = Field(None, description="Notification content")
    reminder_time: Optional[datetime] = Field(None, description="New reminder time (UTC)")

    # Recurrence settings (optional for updates)
    recurrence_type: Optional[RecurrenceTypeEnum] = None
    recurrence_interval: Optional[int] = Field(None, ge=1, le=100)
    recurrence_end_type: Optional[RecurrenceEndTypeEnum] = None
    recurrence_end_value: Optional[str] = None

    @field_validator('reminder_time')
    @classmethod
    def validate_future_time(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure reminder time is in the future"""
        if v is not None and v <= datetime.utcnow():
            raise ValueError('Reminder time must be in the future')
        return v


class ReminderResponse(BaseModel):
    """Schema for reminder response"""
    id: UUID
    user_id: UUID
    note_uuid: str
    title: str
    notification_title: str
    notification_content: Optional[str]
    description: Optional[str]  # Deprecated, for backward compatibility
    reminder_time: datetime
    is_triggered: bool
    triggered_at: Optional[datetime]

    # Recurrence fields
    recurrence_type: str
    recurrence_interval: int
    recurrence_end_type: str
    recurrence_end_value: Optional[str]
    parent_reminder_id: Optional[UUID]
    occurrence_number: int
    series_id: Optional[UUID]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReminderListResponse(BaseModel):
    """Schema for list of reminders"""
    reminders: List[ReminderResponse]
    total: int
    message: str = "Reminders retrieved successfully"


class ReminderSyncItem(BaseModel):
    """Schema for syncing a single reminder from client"""
    note_uuid: str
    title: str
    notification_title: str
    notification_content: Optional[str] = None
    description: Optional[str] = None  # Deprecated, for backward compatibility
    reminder_time: datetime

    # Recurrence fields
    recurrence_type: str = "once"
    recurrence_interval: int = 1
    recurrence_end_type: str = "never"
    recurrence_end_value: Optional[str] = None
    parent_reminder_id: Optional[str] = None
    occurrence_number: int = 1
    series_id: Optional[str] = None


class ReminderSyncRequest(BaseModel):
    """Schema for batch reminder sync (migration from client)"""
    reminders: List[ReminderSyncItem]


class ReminderSyncResponse(BaseModel):
    """Schema for reminder sync response"""
    created: int = Field(..., description="Number of reminders created")
    updated: int = Field(..., description="Number of reminders updated")
    total: int = Field(..., description="Total reminders processed")
    message: str = "Reminders synced successfully"


class ReminderDeleteResponse(BaseModel):
    """Schema for reminder deletion response"""
    message: str = "Reminder deleted successfully"
    deleted_id: UUID

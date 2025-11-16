"""Reminder API schemas"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from uuid import UUID


class ReminderCreate(BaseModel):
    """Schema for creating a new reminder"""
    note_uuid: str = Field(..., description="UUID of the associated note from client")
    title: str = Field(..., max_length=500, description="Reminder title")
    description: Optional[str] = Field(None, description="Optional reminder description")
    reminder_time: datetime = Field(..., description="When to send the reminder (UTC)")


class ReminderUpdate(BaseModel):
    """Schema for updating an existing reminder"""
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    reminder_time: Optional[datetime] = Field(None, description="New reminder time (UTC)")


class ReminderResponse(BaseModel):
    """Schema for reminder response"""
    id: UUID
    user_id: UUID
    note_uuid: str
    title: str
    description: Optional[str]
    reminder_time: datetime
    is_triggered: bool
    triggered_at: Optional[datetime]
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
    description: Optional[str] = None
    reminder_time: datetime


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

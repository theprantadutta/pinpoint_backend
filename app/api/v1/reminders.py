"""Reminder notification endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.schemas.reminder import (
    ReminderCreate,
    ReminderUpdate,
    ReminderResponse,
    ReminderListResponse,
    ReminderSyncRequest,
    ReminderSyncResponse,
    ReminderDeleteResponse
)
from app.services.reminder_service import ReminderService
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("", response_model=ReminderResponse, status_code=201)
async def create_reminder(
    reminder_data: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new reminder

    Creates a reminder in the database and schedules a Celery task
    to send FCM push notification to all user devices at the scheduled time.

    Args:
        reminder_data: Reminder creation data
        current_user: Authenticated user
        db: Database session

    Returns:
        Created reminder
    """
    service = ReminderService(db)

    try:
        reminder = await service.create_reminder(
            user_id=current_user.id,
            reminder_data=reminder_data
        )
        return reminder
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create reminder: {str(e)}"
        )


@router.put("/{reminder_id}", response_model=ReminderResponse)
async def update_reminder(
    reminder_id: UUID,
    reminder_data: ReminderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing reminder

    If the reminder time is updated, the Celery task will be rescheduled.

    Args:
        reminder_id: Reminder ID
        reminder_data: Update data
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated reminder
    """
    service = ReminderService(db)

    try:
        reminder = await service.update_reminder(
            reminder_id=reminder_id,
            user_id=current_user.id,
            reminder_data=reminder_data
        )

        if not reminder:
            raise HTTPException(
                status_code=404,
                detail="Reminder not found"
            )

        return reminder
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update reminder: {str(e)}"
        )


@router.delete("/{reminder_id}", response_model=ReminderDeleteResponse)
async def delete_reminder(
    reminder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a reminder

    Cancels the scheduled Celery task and removes the reminder from database.

    Args:
        reminder_id: Reminder ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Deletion confirmation
    """
    service = ReminderService(db)

    try:
        deleted = await service.delete_reminder(
            reminder_id=reminder_id,
            user_id=current_user.id
        )

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="Reminder not found"
            )

        return ReminderDeleteResponse(
            message="Reminder deleted successfully",
            deleted_id=reminder_id
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete reminder: {str(e)}"
        )


@router.get("", response_model=ReminderListResponse)
async def get_reminders(
    include_triggered: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all reminders for the current user

    Args:
        include_triggered: Whether to include already triggered reminders
        current_user: Authenticated user
        db: Database session

    Returns:
        List of reminders
    """
    service = ReminderService(db)

    try:
        reminders = await service.get_user_reminders(
            user_id=current_user.id,
            include_triggered=include_triggered
        )

        return ReminderListResponse(
            reminders=reminders,
            total=len(reminders)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve reminders: {str(e)}"
        )


@router.get("/{reminder_id}", response_model=ReminderResponse)
async def get_reminder(
    reminder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific reminder

    Args:
        reminder_id: Reminder ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Reminder
    """
    service = ReminderService(db)

    try:
        reminder = await service.get_reminder(
            reminder_id=reminder_id,
            user_id=current_user.id
        )

        if not reminder:
            raise HTTPException(
                status_code=404,
                detail="Reminder not found"
            )

        return reminder
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve reminder: {str(e)}"
        )


@router.post("/sync", response_model=ReminderSyncResponse)
async def sync_reminders(
    request: ReminderSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Bulk sync reminders from client (for migration)

    This endpoint is used for one-time migration of existing client-side
    reminders to the backend. It creates or updates reminders and schedules
    corresponding Celery tasks.

    Args:
        request: List of reminders to sync
        current_user: Authenticated user
        db: Database session

    Returns:
        Sync result with created/updated counts
    """
    service = ReminderService(db)

    try:
        result = await service.sync_reminders(
            user_id=current_user.id,
            reminders=request.reminders
        )

        return ReminderSyncResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync reminders: {str(e)}"
        )

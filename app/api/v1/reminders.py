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


@router.post("", response_model=List[ReminderResponse], status_code=201)
async def create_reminder(
    reminder_data: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create new reminder(s)

    Creates reminders in the database and schedules tasks to send FCM push notifications.
    For recurring reminders, creates multiple occurrences (up to 100 or 1 year ahead).

    Args:
        reminder_data: Reminder creation data
        current_user: Authenticated user
        db: Database session

    Returns:
        List of created reminders (single for one-time, multiple for recurring)
    """
    service = ReminderService(db)

    try:
        reminders = await service.create_reminder(
            user_id=current_user.id,
            reminder_data=reminder_data
        )
        return reminders
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create reminder: {str(e)}"
        )


@router.put("/{reminder_id}", response_model=List[ReminderResponse])
async def update_reminder(
    reminder_id: UUID,
    reminder_data: ReminderUpdate,
    update_series: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an existing reminder or series

    If the reminder time is updated, the task(s) will be rescheduled.
    Use update_series=true to update all future occurrences in a recurring series.

    Args:
        reminder_id: Reminder ID
        reminder_data: Update data
        update_series: If true, update all future occurrences in the series
        current_user: Authenticated user
        db: Database session

    Returns:
        List of updated reminders
    """
    service = ReminderService(db)

    try:
        reminders = await service.update_reminder(
            reminder_id=reminder_id,
            user_id=current_user.id,
            reminder_data=reminder_data,
            update_series=update_series
        )

        if not reminders:
            raise HTTPException(
                status_code=404,
                detail="Reminder not found"
            )

        return reminders
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
    delete_series: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a reminder or entire series

    Cancels scheduled task(s) and removes reminder(s) from database.
    Use delete_series=true to delete all occurrences in a recurring series.

    Args:
        reminder_id: Reminder ID
        delete_series: If true, delete all occurrences in the series
        current_user: Authenticated user
        db: Session database

    Returns:
        Deletion confirmation
    """
    service = ReminderService(db)

    try:
        success, deleted_count = await service.delete_reminder(
            reminder_id=reminder_id,
            user_id=current_user.id,
            delete_series=delete_series
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail="Reminder not found"
            )

        message = f"Deleted {deleted_count} reminder(s) successfully"
        if delete_series and deleted_count > 1:
            message = f"Deleted series: {deleted_count} reminders"

        return ReminderDeleteResponse(
            message=message,
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


@router.post("/{reminder_id}/trigger-now", response_model=dict)
async def trigger_reminder_now(
    reminder_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    DEBUG: Manually trigger a reminder notification immediately

    This endpoint is for testing - it sends the notification right away
    without waiting for the scheduled time.
    """
    from app.tasks.reminder_tasks import send_reminder_notification

    # Verify reminder exists and belongs to user
    from app.models.reminder import Reminder
    reminder = db.query(Reminder).filter(
        Reminder.id == reminder_id,
        Reminder.user_id == current_user.id
    ).first()

    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    # Trigger the notification
    result = send_reminder_notification(str(reminder_id))

    return {
        "success": True,
        "message": "Notification triggered",
        "result": result
    }


@router.get("/debug/scheduled-jobs", response_model=dict)
async def get_scheduled_jobs(
    current_user: User = Depends(get_current_user)
):
    """
    DEBUG: Get list of all scheduled reminder jobs in APScheduler
    """
    from app.scheduler import scheduler

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
            "func_name": job.func.__name__ if hasattr(job, 'func') else None
        })

    return {
        "scheduler_running": scheduler.running,
        "total_jobs": len(jobs),
        "jobs": jobs
    }

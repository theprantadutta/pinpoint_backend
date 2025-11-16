"""Reminder service for backend-controlled notification scheduling"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.reminder import Reminder
from app.schemas.reminder import (
    ReminderCreate,
    ReminderUpdate,
    ReminderSyncItem
)
from datetime import datetime
from typing import List, Optional, Dict
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing reminders and scheduling notifications"""

    def __init__(self, db: Session):
        self.db = db

    async def create_reminder(
        self,
        user_id: UUID,
        reminder_data: ReminderCreate
    ) -> Reminder:
        """
        Create a new reminder and schedule Celery task

        Args:
            user_id: User ID
            reminder_data: Reminder creation data

        Returns:
            Created reminder
        """
        # Create reminder in database
        reminder = Reminder(
            user_id=user_id,
            note_uuid=reminder_data.note_uuid,
            title=reminder_data.title,
            description=reminder_data.description,
            reminder_time=reminder_data.reminder_time,
            is_triggered=False
        )

        self.db.add(reminder)
        self.db.commit()
        self.db.refresh(reminder)

        # Schedule Celery task (will be implemented after Celery setup)
        try:
            task_id = await self._schedule_reminder_task(reminder)
            reminder.celery_task_id = task_id
            self.db.commit()
            logger.info(f"Scheduled reminder {reminder.id} with Celery task {task_id}")
        except Exception as e:
            logger.error(f"Failed to schedule reminder {reminder.id}: {e}")
            # Don't fail the whole operation if scheduling fails
            # The catch-up job will handle it

        return reminder

    async def update_reminder(
        self,
        reminder_id: UUID,
        user_id: UUID,
        reminder_data: ReminderUpdate
    ) -> Optional[Reminder]:
        """
        Update existing reminder and reschedule if time changed

        Args:
            reminder_id: Reminder ID
            user_id: User ID (for authorization)
            reminder_data: Update data

        Returns:
            Updated reminder or None if not found
        """
        # Get reminder and verify ownership
        reminder = self.db.query(Reminder).filter(
            and_(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id
            )
        ).first()

        if not reminder:
            return None

        # Check if reminder time is being updated
        time_changed = (
            reminder_data.reminder_time is not None
            and reminder_data.reminder_time != reminder.reminder_time
        )

        # Update fields
        if reminder_data.title is not None:
            reminder.title = reminder_data.title
        if reminder_data.description is not None:
            reminder.description = reminder_data.description
        if reminder_data.reminder_time is not None:
            reminder.reminder_time = reminder_data.reminder_time

        self.db.commit()
        self.db.refresh(reminder)

        # Reschedule if time changed
        if time_changed and not reminder.is_triggered:
            try:
                # Cancel old task
                if reminder.celery_task_id:
                    await self._cancel_reminder_task(reminder.celery_task_id)

                # Schedule new task
                task_id = await self._schedule_reminder_task(reminder)
                reminder.celery_task_id = task_id
                self.db.commit()
                logger.info(f"Rescheduled reminder {reminder.id} with new task {task_id}")
            except Exception as e:
                logger.error(f"Failed to reschedule reminder {reminder.id}: {e}")

        return reminder

    async def delete_reminder(
        self,
        reminder_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Delete reminder and cancel Celery task

        Args:
            reminder_id: Reminder ID
            user_id: User ID (for authorization)

        Returns:
            True if deleted, False if not found
        """
        reminder = self.db.query(Reminder).filter(
            and_(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id
            )
        ).first()

        if not reminder:
            return False

        # Cancel Celery task if exists
        if reminder.celery_task_id and not reminder.is_triggered:
            try:
                await self._cancel_reminder_task(reminder.celery_task_id)
                logger.info(f"Cancelled Celery task {reminder.celery_task_id} for reminder {reminder.id}")
            except Exception as e:
                logger.error(f"Failed to cancel task {reminder.celery_task_id}: {e}")

        # Delete from database
        self.db.delete(reminder)
        self.db.commit()
        return True

    async def get_user_reminders(
        self,
        user_id: UUID,
        include_triggered: bool = True
    ) -> List[Reminder]:
        """
        Get all reminders for a user

        Args:
            user_id: User ID
            include_triggered: Whether to include already triggered reminders

        Returns:
            List of reminders
        """
        query = self.db.query(Reminder).filter(Reminder.user_id == user_id)

        if not include_triggered:
            query = query.filter(Reminder.is_triggered == False)

        return query.order_by(Reminder.reminder_time.asc()).all()

    async def get_reminder(
        self,
        reminder_id: UUID,
        user_id: UUID
    ) -> Optional[Reminder]:
        """
        Get a specific reminder

        Args:
            reminder_id: Reminder ID
            user_id: User ID (for authorization)

        Returns:
            Reminder or None
        """
        return self.db.query(Reminder).filter(
            and_(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id
            )
        ).first()

    async def sync_reminders(
        self,
        user_id: UUID,
        reminders: List[ReminderSyncItem]
    ) -> Dict[str, int]:
        """
        Bulk sync reminders from client (for migration)

        Args:
            user_id: User ID
            reminders: List of reminders to sync

        Returns:
            Dictionary with created/updated counts
        """
        created = 0
        updated = 0

        for reminder_data in reminders:
            # Check if reminder already exists for this note_uuid
            existing = self.db.query(Reminder).filter(
                and_(
                    Reminder.user_id == user_id,
                    Reminder.note_uuid == reminder_data.note_uuid
                )
            ).first()

            if existing:
                # Update existing reminder
                existing.title = reminder_data.title
                existing.description = reminder_data.description
                existing.reminder_time = reminder_data.reminder_time
                updated += 1
            else:
                # Create new reminder
                new_reminder = Reminder(
                    user_id=user_id,
                    note_uuid=reminder_data.note_uuid,
                    title=reminder_data.title,
                    description=reminder_data.description,
                    reminder_time=reminder_data.reminder_time,
                    is_triggered=False
                )
                self.db.add(new_reminder)
                created += 1

                # Schedule Celery task for new reminders
                try:
                    self.db.flush()  # Get the ID
                    task_id = await self._schedule_reminder_task(new_reminder)
                    new_reminder.celery_task_id = task_id
                except Exception as e:
                    logger.error(f"Failed to schedule synced reminder: {e}")

        self.db.commit()

        return {
            "created": created,
            "updated": updated,
            "total": created + updated
        }

    async def get_due_reminders(self) -> List[Reminder]:
        """
        Get reminders that are due to be triggered (for catch-up job)

        Returns:
            List of due reminders
        """
        now = datetime.utcnow()
        return self.db.query(Reminder).filter(
            and_(
                Reminder.is_triggered == False,
                Reminder.reminder_time <= now
            )
        ).all()

    async def mark_triggered(self, reminder: Reminder):
        """
        Mark reminder as triggered

        Args:
            reminder: Reminder to mark
        """
        reminder.mark_triggered()
        self.db.commit()

    # Celery task management methods
    async def _schedule_reminder_task(self, reminder: Reminder) -> str:
        """
        Schedule Celery task for reminder

        Returns:
            Celery task ID
        """
        try:
            from app.tasks.reminder_tasks import send_reminder_notification

            # Calculate countdown in seconds until reminder time
            now = datetime.utcnow()
            countdown = (reminder.reminder_time - now).total_seconds()

            # Don't schedule tasks in the past
            if countdown < 0:
                logger.warning(f"Reminder {reminder.id} is in the past, scheduling immediately")
                countdown = 0

            # Schedule the task
            result = send_reminder_notification.apply_async(
                args=[str(reminder.id)],
                eta=reminder.reminder_time  # Execute at exact time
            )

            logger.info(f"Scheduled Celery task {result.id} for reminder {reminder.id} at {reminder.reminder_time}")
            return result.id

        except Exception as e:
            logger.error(f"Failed to schedule Celery task for reminder {reminder.id}: {e}")
            raise

    async def _cancel_reminder_task(self, task_id: str):
        """
        Cancel scheduled Celery task

        Args:
            task_id: Celery task ID to cancel
        """
        try:
            from celery_app import celery_app

            # Revoke the task
            celery_app.control.revoke(task_id, terminate=True)
            logger.info(f"Cancelled Celery task {task_id}")

        except Exception as e:
            logger.error(f"Failed to cancel Celery task {task_id}: {e}")
            raise

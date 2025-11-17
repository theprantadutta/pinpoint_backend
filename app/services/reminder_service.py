"""Reminder service for backend-controlled notification scheduling"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.reminder import Reminder, RecurrenceType, RecurrenceEndType
from app.schemas.reminder import (
    ReminderCreate,
    ReminderUpdate,
    ReminderSyncItem
)
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Dict, Tuple
from uuid import UUID, uuid4
import logging

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing reminders and scheduling notifications"""

    def __init__(self, db: Session):
        self.db = db

    def _generate_occurrence_times(
        self,
        start_time: datetime,
        recurrence_type: str,
        recurrence_interval: int,
        recurrence_end_type: str,
        recurrence_end_value: Optional[str],
        max_occurrences: int = 100
    ) -> List[datetime]:
        """
        Generate list of occurrence times for recurring reminder

        Args:
            start_time: First occurrence time
            recurrence_type: Type of recurrence (once, hourly, daily, etc.)
            recurrence_interval: Interval (e.g., every 2 days)
            recurrence_end_type: How recurrence ends (never, after_occurrences, on_date)
            recurrence_end_value: Number or ISO date string
            max_occurrences: Maximum occurrences to generate (default 100)

        Returns:
            List of datetime occurrences
        """
        if recurrence_type == "once":
            return [start_time]

        occurrences = [start_time]
        current_time = start_time

        # Determine end condition
        max_count = max_occurrences
        end_date = None

        if recurrence_end_type == "after_occurrences" and recurrence_end_value:
            max_count = min(int(recurrence_end_value), max_occurrences)
        elif recurrence_end_type == "on_date" and recurrence_end_value:
            end_date = datetime.fromisoformat(recurrence_end_value.replace('Z', '+00:00'))
            if end_date.tzinfo:
                end_date = end_date.replace(tzinfo=None)

        # Generate occurrences
        while len(occurrences) < max_count:
            # Calculate next occurrence
            if recurrence_type == "hourly":
                current_time = current_time + timedelta(hours=recurrence_interval)
            elif recurrence_type == "daily":
                current_time = current_time + timedelta(days=recurrence_interval)
            elif recurrence_type == "weekly":
                current_time = current_time + timedelta(weeks=recurrence_interval)
            elif recurrence_type == "monthly":
                current_time = current_time + relativedelta(months=recurrence_interval)
            elif recurrence_type == "yearly":
                current_time = current_time + relativedelta(years=recurrence_interval)
            else:
                break

            # Check end date
            if end_date and current_time > end_date:
                break

            # Don't generate occurrences more than 1 year in the future
            one_year_ahead = datetime.utcnow() + timedelta(days=365)
            if current_time > one_year_ahead:
                break

            occurrences.append(current_time)

        return occurrences

    async def create_reminder(
        self,
        user_id: UUID,
        reminder_data: ReminderCreate
    ) -> List[Reminder]:
        """
        Create reminder(s) and schedule tasks
        For recurring reminders, generates and creates all occurrences

        Args:
            user_id: User ID
            reminder_data: Reminder creation data

        Returns:
            List of created reminders (single for one-time, multiple for recurring)
        """
        # Generate occurrence times
        logger.info(f"Creating reminder for user {user_id}: type={reminder_data.recurrence_type.value}, interval={reminder_data.recurrence_interval}")
        occurrence_times = self._generate_occurrence_times(
            start_time=reminder_data.reminder_time,
            recurrence_type=reminder_data.recurrence_type.value,
            recurrence_interval=reminder_data.recurrence_interval,
            recurrence_end_type=reminder_data.recurrence_end_type.value,
            recurrence_end_value=reminder_data.recurrence_end_value
        )
        logger.info(f"Generated {len(occurrence_times)} occurrence(s) for reminder")

        # Generate series ID for recurring reminders
        series_id = uuid4() if reminder_data.recurrence_type != "once" else None
        reminders = []
        parent_id = None

        for idx, occurrence_time in enumerate(occurrence_times):
            # Create reminder for this occurrence
            reminder = Reminder(
                user_id=user_id,
                note_uuid=reminder_data.note_uuid,
                title=reminder_data.title,
                notification_title=reminder_data.notification_title,
                notification_content=reminder_data.notification_content,
                reminder_time=occurrence_time,
                is_triggered=False,
                recurrence_type=reminder_data.recurrence_type.value,
                recurrence_interval=reminder_data.recurrence_interval,
                recurrence_end_type=reminder_data.recurrence_end_type.value,
                recurrence_end_value=reminder_data.recurrence_end_value,
                occurrence_number=idx + 1,
                series_id=series_id,
                parent_reminder_id=parent_id
            )

            self.db.add(reminder)
            self.db.flush()  # Get the ID

            # First occurrence is the parent
            if idx == 0:
                parent_id = reminder.id

            # Schedule task
            try:
                task_id = await self._schedule_reminder_task(reminder)
                reminder.celery_task_id = task_id
                logger.info(f"Scheduled reminder {reminder.id} occurrence {idx+1} at {occurrence_time}")
            except Exception as e:
                logger.error(f"Failed to schedule reminder {reminder.id}: {e}")

            reminders.append(reminder)

        self.db.commit()

        # Refresh all reminders
        for reminder in reminders:
            self.db.refresh(reminder)

        logger.info(f"Created {len(reminders)} reminder occurrence(s) for user {user_id}")
        return reminders

    async def update_reminder(
        self,
        reminder_id: UUID,
        user_id: UUID,
        reminder_data: ReminderUpdate,
        update_series: bool = False
    ) -> Optional[List[Reminder]]:
        """
        Update existing reminder and reschedule if time changed
        Can update single occurrence or entire series

        Args:
            reminder_id: Reminder ID
            user_id: User ID (for authorization)
            reminder_data: Update data
            update_series: If True, update all occurrences in the series

        Returns:
            List of updated reminders or None if not found
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

        # Determine which reminders to update
        if update_series and reminder.series_id:
            # Update all occurrences in the series
            reminders_to_update = self.db.query(Reminder).filter(
                and_(
                    Reminder.user_id == user_id,
                    Reminder.series_id == reminder.series_id,
                    Reminder.is_triggered == False  # Only update future occurrences
                )
            ).all()
        else:
            # Update only this reminder
            reminders_to_update = [reminder]

        updated_reminders = []

        for rem in reminders_to_update:
            # Check if reminder time is being updated
            time_changed = (
                reminder_data.reminder_time is not None
                and reminder_data.reminder_time != rem.reminder_time
            )

            # Update fields
            if reminder_data.title is not None:
                rem.title = reminder_data.title
            if reminder_data.notification_title is not None:
                rem.notification_title = reminder_data.notification_title
            if reminder_data.notification_content is not None:
                rem.notification_content = reminder_data.notification_content
            if reminder_data.reminder_time is not None:
                rem.reminder_time = reminder_data.reminder_time
            if reminder_data.recurrence_type is not None:
                rem.recurrence_type = reminder_data.recurrence_type.value
            if reminder_data.recurrence_interval is not None:
                rem.recurrence_interval = reminder_data.recurrence_interval

            # Reschedule if time changed
            if time_changed and not rem.is_triggered:
                try:
                    # Cancel old task
                    if rem.celery_task_id:
                        await self._cancel_reminder_task(rem.celery_task_id)

                    # Schedule new task
                    task_id = await self._schedule_reminder_task(rem)
                    rem.celery_task_id = task_id
                    logger.info(f"Rescheduled reminder {rem.id} with new task {task_id}")
                except Exception as e:
                    logger.error(f"Failed to reschedule reminder {rem.id}: {e}")

            updated_reminders.append(rem)

        self.db.commit()

        # Refresh all reminders
        for rem in updated_reminders:
            self.db.refresh(rem)

        return updated_reminders

    async def delete_reminder(
        self,
        reminder_id: UUID,
        user_id: UUID,
        delete_series: bool = False
    ) -> Tuple[bool, int]:
        """
        Delete reminder and cancel scheduled task
        Can delete single occurrence or entire series

        Args:
            reminder_id: Reminder ID
            user_id: User ID (for authorization)
            delete_series: If True, delete all occurrences in the series

        Returns:
            Tuple of (success: bool, deleted_count: int)
        """
        reminder = self.db.query(Reminder).filter(
            and_(
                Reminder.id == reminder_id,
                Reminder.user_id == user_id
            )
        ).first()

        if not reminder:
            return (False, 0)

        # Determine which reminders to delete
        if delete_series and reminder.series_id:
            # Delete all occurrences in the series (including triggered ones)
            reminders_to_delete = self.db.query(Reminder).filter(
                and_(
                    Reminder.user_id == user_id,
                    Reminder.series_id == reminder.series_id
                )
            ).all()
        else:
            # Delete only this reminder
            reminders_to_delete = [reminder]

        deleted_count = 0

        for rem in reminders_to_delete:
            # Cancel task if exists and not triggered
            if rem.celery_task_id and not rem.is_triggered:
                try:
                    await self._cancel_reminder_task(rem.celery_task_id)
                    logger.info(f"Cancelled task {rem.celery_task_id} for reminder {rem.id}")
                except Exception as e:
                    logger.error(f"Failed to cancel task {rem.celery_task_id}: {e}")

            # Delete from database
            self.db.delete(rem)
            deleted_count += 1

        self.db.commit()
        logger.info(f"Deleted {deleted_count} reminder(s)")
        return (True, deleted_count)

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
        Bulk sync reminders from client

        Args:
            user_id: User ID
            reminders: List of reminders to sync

        Returns:
            Dictionary with created/updated counts
        """
        created = 0
        updated = 0

        for reminder_data in reminders:
            # For sync, we check by note_uuid and occurrence_number to find exact occurrence
            existing = self.db.query(Reminder).filter(
                and_(
                    Reminder.user_id == user_id,
                    Reminder.note_uuid == reminder_data.note_uuid,
                    Reminder.occurrence_number == reminder_data.occurrence_number
                )
            ).first()

            if existing:
                # Update existing reminder
                existing.title = reminder_data.title
                existing.notification_title = reminder_data.notification_title
                existing.notification_content = reminder_data.notification_content
                existing.reminder_time = reminder_data.reminder_time
                existing.recurrence_type = reminder_data.recurrence_type
                existing.recurrence_interval = reminder_data.recurrence_interval
                existing.recurrence_end_type = reminder_data.recurrence_end_type
                existing.recurrence_end_value = reminder_data.recurrence_end_value
                if reminder_data.series_id:
                    existing.series_id = UUID(reminder_data.series_id)
                updated += 1
            else:
                # Create new reminder
                new_reminder = Reminder(
                    user_id=user_id,
                    note_uuid=reminder_data.note_uuid,
                    title=reminder_data.title,
                    notification_title=reminder_data.notification_title,
                    notification_content=reminder_data.notification_content,
                    reminder_time=reminder_data.reminder_time,
                    is_triggered=False,
                    recurrence_type=reminder_data.recurrence_type,
                    recurrence_interval=reminder_data.recurrence_interval,
                    recurrence_end_type=reminder_data.recurrence_end_type,
                    recurrence_end_value=reminder_data.recurrence_end_value,
                    occurrence_number=reminder_data.occurrence_number,
                    series_id=UUID(reminder_data.series_id) if reminder_data.series_id else None
                )
                self.db.add(new_reminder)
                created += 1

                # Schedule task for new reminders
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
        Schedule reminder task using APScheduler

        Returns:
            Job ID
        """
        try:
            from app.scheduler import schedule_reminder
            from datetime import datetime

            logger.info(f"📅 Scheduling reminder {reminder.id} for {reminder.reminder_time} (current time: {datetime.utcnow()})")

            # Schedule the task
            job_id = schedule_reminder(
                reminder_id=str(reminder.id),
                reminder_time=reminder.reminder_time
            )

            logger.info(f"✅ Successfully scheduled reminder {reminder.id} with job_id={job_id}")
            return job_id

        except Exception as e:
            logger.error(f"❌ Failed to schedule reminder {reminder.id}: {e}", exc_info=True)
            raise

    async def _cancel_reminder_task(self, task_id: str):
        """
        Cancel scheduled reminder task

        Args:
            task_id: Job ID to cancel
        """
        try:
            from app.scheduler import cancel_reminder

            # Cancel the job
            cancel_reminder(task_id)
            logger.info(f"Cancelled reminder job {task_id}")

        except Exception as e:
            logger.error(f"Failed to cancel reminder job {task_id}: {e}")
            raise

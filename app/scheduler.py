"""Simple reminder scheduler using APScheduler"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = BackgroundScheduler(timezone="UTC")


def start_scheduler():
    """Start the background scheduler"""
    if not scheduler.running:
        scheduler.start()
        logger.info("✅ Reminder scheduler started")


def stop_scheduler():
    """Stop the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("👋 Reminder scheduler stopped")


def schedule_reminder(reminder_id: str, reminder_time: datetime):
    """
    Schedule a reminder to be sent at a specific time

    Args:
        reminder_id: UUID of the reminder
        reminder_time: When to send the reminder (UTC)

    Returns:
        Job ID
    """
    from app.tasks.reminder_tasks import send_reminder_notification

    job = scheduler.add_job(
        send_reminder_notification,
        trigger=DateTrigger(run_date=reminder_time),
        args=[reminder_id],
        id=f"reminder_{reminder_id}",
        replace_existing=True,
        misfire_grace_time=300,  # Allow up to 5 minutes late execution
    )

    logger.info(f"📅 Scheduled reminder {reminder_id} for {reminder_time}")
    return job.id


def cancel_reminder(job_id: str):
    """
    Cancel a scheduled reminder

    Args:
        job_id: Job ID to cancel
    """
    try:
        scheduler.remove_job(job_id)
        logger.info(f"❌ Cancelled reminder job {job_id}")
    except Exception as e:
        logger.warning(f"Failed to cancel job {job_id}: {e}")


def check_missed_reminders():
    """
    Check for reminders that should have been sent but weren't
    This runs periodically to catch any that were missed
    """
    from app.tasks.reminder_tasks import check_missed_reminders as check_task
    check_task()


# Schedule the periodic missed reminder check
scheduler.add_job(
    check_missed_reminders,
    trigger='interval',
    minutes=5,
    id='check_missed_reminders',
    replace_existing=True,
)

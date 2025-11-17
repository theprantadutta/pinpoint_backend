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
    try:
        print("="*70)
        print("🚀 STARTING APSCHEDULER...")
        print(f"Scheduler running before start: {scheduler.running}")
        print("="*70)

        if not scheduler.running:
            logger.info("🚀 Starting APScheduler...")
            scheduler.start()

            print(f"✅ Scheduler started! Running: {scheduler.running}")
            logger.info("✅ Reminder scheduler started")
            logger.info(f"📊 Scheduler state: running={scheduler.running}, jobstores={list(scheduler._jobstores.keys())}")

            # Add periodic missed reminder check
            print("Adding periodic missed reminder check...")
            scheduler.add_job(
                check_missed_reminders,
                trigger='interval',
                minutes=5,
                id='check_missed_reminders',
                replace_existing=True,
            )
            print("✅ Added periodic check job")
            logger.info("✅ Added periodic missed reminder check (every 5 minutes)")

            # Log all existing jobs
            jobs = scheduler.get_jobs()
            print(f"📋 Total jobs in scheduler: {len(jobs)}")
            logger.info(f"📋 Current jobs in scheduler: {len(jobs)}")
            for job in jobs:
                print(f"  - Job: {job.id}, next_run: {job.next_run_time}")
                logger.info(f"  - Job: {job.id}, next_run: {job.next_run_time}")

            print("="*70)
            print("✅ SCHEDULER INITIALIZATION COMPLETE")
            print("="*70)
        else:
            logger.info("⚠️ Scheduler already running")
            print("⚠️ Scheduler already running")
    except Exception as e:
        print(f"❌❌❌ CRITICAL ERROR: Failed to start scheduler: {e}")
        logger.error(f"❌ Failed to start scheduler: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise


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
    from datetime import datetime

    try:
        current_time = datetime.utcnow()
        time_diff = (reminder_time - current_time).total_seconds()

        logger.info(f"🔔 Scheduling reminder {reminder_id}")
        logger.info(f"  Current time (UTC): {current_time}")
        logger.info(f"  Scheduled time (UTC): {reminder_time}")
        logger.info(f"  Time until trigger: {time_diff:.1f} seconds ({time_diff/60:.1f} minutes)")
        logger.info(f"  Scheduler running: {scheduler.running}")

        job = scheduler.add_job(
            send_reminder_notification,
            trigger=DateTrigger(run_date=reminder_time),
            args=[reminder_id],
            id=f"reminder_{reminder_id}",
            replace_existing=True,
            misfire_grace_time=300,  # Allow up to 5 minutes late execution
        )

        logger.info(f"✅ Reminder {reminder_id} scheduled successfully with job_id={job.id}")
        logger.info(f"  Next run time: {job.next_run_time}")

        # List all jobs after adding
        all_jobs = scheduler.get_jobs()
        logger.info(f"📊 Total jobs in scheduler: {len(all_jobs)}")

        return job.id

    except Exception as e:
        logger.error(f"❌ Failed to schedule reminder {reminder_id}: {e}", exc_info=True)
        raise


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
    logger.info("🔍 Running periodic check for missed reminders...")
    result = check_task()
    logger.info(f"✅ Missed reminder check complete: {result}")

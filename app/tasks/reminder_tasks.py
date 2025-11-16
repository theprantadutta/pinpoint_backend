"""Tasks for reminder notifications"""
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import UUID
import logging
import asyncio

from app.database import SessionLocal
from app.models.reminder import Reminder
from app.models.notification import FCMToken
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def send_reminder_notification(reminder_id: str):
    """
    Send FCM push notification for a reminder to all user devices

    This task is scheduled by Celery at the reminder's scheduled time.
    It sends notifications to all registered devices for the user.

    Args:
        reminder_id: UUID of the reminder to trigger

    Returns:
        Dictionary with success status and message
    """
    db: Session = SessionLocal()

    try:
        # Get the reminder
        reminder = db.query(Reminder).filter(
            Reminder.id == UUID(reminder_id)
        ).first()

        if not reminder:
            logger.error(f"Reminder {reminder_id} not found")
            return {
                "success": False,
                "message": f"Reminder {reminder_id} not found"
            }

        # Check if already triggered
        if reminder.is_triggered:
            logger.warning(f"Reminder {reminder_id} already triggered")
            return {
                "success": True,
                "message": "Reminder already triggered"
            }

        # Get all FCM tokens for the user
        fcm_tokens = db.query(FCMToken).filter(
            FCMToken.user_id == reminder.user_id
        ).all()

        if not fcm_tokens:
            logger.warning(f"No FCM tokens found for user {reminder.user_id}")
            # Still mark as triggered even if no devices
            reminder.mark_triggered()
            db.commit()
            return {
                "success": False,
                "message": "No FCM tokens found for user"
            }

        # Send notification to all devices
        notification_service = NotificationService(db)
        sent_count = 0
        failed_count = 0

        for token in fcm_tokens:
            try:
                # Run the async send_notification method
                result = asyncio.run(notification_service.send_notification(
                    fcm_token=token.fcm_token,
                    title=f"⏰ {reminder.title}",
                    body=reminder.description or "Reminder notification",
                    data={
                        "type": "reminder",
                        "reminder_id": str(reminder.id),
                        "note_uuid": reminder.note_uuid,
                        "action": "open_note"
                    }
                ))

                if result.get("success"):
                    sent_count += 1
                    logger.info(f"Sent reminder to device {token.device_id}")
                else:
                    failed_count += 1
                    logger.error(f"Failed to send to device {token.device_id}: {result.get('message')}")

            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending to device {token.device_id}: {e}")

        # Mark reminder as triggered
        reminder.mark_triggered()
        db.commit()

        logger.info(
            f"Reminder {reminder_id} triggered: "
            f"sent to {sent_count}/{len(fcm_tokens)} devices"
        )

        return {
            "success": True,
            "message": f"Sent to {sent_count} device(s), {failed_count} failed",
            "sent_count": sent_count,
            "failed_count": failed_count
        }

    except Exception as e:
        logger.error(f"Error in send_reminder_notification: {e}")
        db.rollback()
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

    finally:
        db.close()


def check_missed_reminders():
    """
    Periodic task to check for and trigger any missed reminders

    This runs every 5 minutes to handle:
    - Reminders that failed to schedule
    - Reminders during server downtime
    - Any other edge cases

    Returns:
        Dictionary with number of triggered reminders
    """
    db: Session = SessionLocal()
    triggered_count = 0

    try:
        # Get all reminders that are past due but not triggered
        now = datetime.utcnow()
        missed_reminders = db.query(Reminder).filter(
            Reminder.is_triggered == False,
            Reminder.reminder_time <= now
        ).all()

        logger.info(f"Found {len(missed_reminders)} missed reminders")

        for reminder in missed_reminders:
            try:
                # Trigger the reminder immediately
                send_reminder_notification(str(reminder.id))
                triggered_count += 1
                logger.info(f"Sent missed reminder {reminder.id}")

            except Exception as e:
                logger.error(f"Failed to send missed reminder {reminder.id}: {e}")

        return {
            "success": True,
            "triggered_count": triggered_count,
            "message": f"Sent {triggered_count} missed reminders"
        }

    except Exception as e:
        logger.error(f"Error in check_missed_reminders: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

    finally:
        db.close()

"""Celery application configuration"""
from celery import Celery
from celery.schedules import crontab
from app.config import settings
import os

# Create Celery app
celery_app = Celery(
    "pinpoint",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.reminder_tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Timezone configuration
    timezone="UTC",
    enable_utc=True,

    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour

    # Worker settings
    worker_prefetch_multiplier=1,  # Don't prefetch tasks
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks to prevent memory leaks

    # Beat schedule for periodic tasks
    beat_schedule={
        "check-missed-reminders": {
            "task": "app.tasks.reminder_tasks.check_missed_reminders",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
    },
)

# Autodiscover tasks
celery_app.autodiscover_tasks(["app.tasks"])

if __name__ == "__main__":
    celery_app.start()

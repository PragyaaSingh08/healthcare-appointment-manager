from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "healthcare_appointment_manager",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.email_worker",
        "app.workers.calendar_worker",
        "app.workers.reminder_worker",
        "app.workers.rag_worker",
        "app.workers.hold_cleanup_worker",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,  # don't ack until the task finishes, so a crashed worker retries it
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "cleanup-expired-holds-every-minute": {
        "task": "app.workers.hold_cleanup_worker.cleanup_expired_holds_task",
        "schedule": 60.0,
    },
    "process-pending-notifications-every-30s": {
        "task": "app.workers.email_worker.process_pending_notifications_task",
        "schedule": 30.0,
    },
    "process-due-medication-reminders-every-minute": {
        "task": "app.workers.reminder_worker.process_due_reminders_task",
        "schedule": 60.0,
    },
    "sync-pending-calendar-events-every-minute": {
        "task": "app.workers.calendar_worker.sync_pending_calendar_events_task",
        "schedule": 60.0,
    },
}

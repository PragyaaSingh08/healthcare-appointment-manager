"""EmailWorker — processes queued Notification rows independently per
recipient (req #46), with exponential backoff retry for transient failures
and a hard retry ceiling (req #47).
"""
import logging
from datetime import timedelta

from app.core.config import get_settings
from app.core.db import session_scope
from app.models.base import NotificationStatus, NotificationType
from app.models.messaging import Notification
from app.services.email_service import EmailPermanentError, EmailTransientError, get_email_provider
from app.utils.timeutils import utcnow
from app.workers.celery_app import celery_app

logger = logging.getLogger("email_worker")
settings = get_settings()

_SUBJECTS = {
    NotificationType.BOOKING_CONFIRMATION: "Your appointment is confirmed",
    NotificationType.REMINDER: "Upcoming appointment reminder",
    NotificationType.CANCELLATION: "Appointment cancelled",
    NotificationType.RESCHEDULE: "Appointment rescheduled",
    NotificationType.LEAVE_CONFLICT: "Your doctor is unavailable — action needed",
    NotificationType.MEDICATION_REMINDER: "Medication reminder",
}


def _build_body(notification: Notification) -> str:
    return (
        f"Notification type: {notification.notification_type.value}\n"
        f"Appointment reference: {notification.appointment_id}\n\n"
        "This is an automated message from the clinic's appointment system."
    )


@celery_app.task(name="app.workers.email_worker.send_notification_task", bind=True, max_retries=None)
def send_notification_task(self, notification_id: str) -> None:
    """Idempotent: re-running for an already-SENT notification is a no-op."""
    with session_scope() as db:
        notification = db.get(Notification, notification_id)
        if not notification or notification.status == NotificationStatus.SENT:
            return

        notification.status = NotificationStatus.PROCESSING
        notification.attempt_count += 1
        db.flush()

        provider = get_email_provider()
        subject = _SUBJECTS.get(notification.notification_type, "Clinic notification")
        body = _build_body(notification)

        try:
            provider.send(notification.recipient, subject, body)
            notification.status = NotificationStatus.SENT
            notification.sent_at = utcnow()
        except EmailPermanentError as e:
            notification.status = NotificationStatus.FAILED
            notification.last_error = str(e)
            logger.error("Permanent email failure for notification %s: %s", notification_id, e)
        except EmailTransientError as e:
            notification.last_error = str(e)
            if notification.attempt_count >= settings.NOTIFICATION_MAX_ATTEMPTS:
                notification.status = NotificationStatus.FAILED
                logger.error("Notification %s exhausted retries: %s", notification_id, e)
            else:
                notification.status = NotificationStatus.PENDING
                backoff_seconds = min(2 ** notification.attempt_count, 300)
                notification.scheduled_at = utcnow() + timedelta(seconds=backoff_seconds)
                logger.warning("Transient email failure for %s, retrying in %ss: %s", notification_id, backoff_seconds, e)


@celery_app.task(name="app.workers.email_worker.process_pending_notifications_task")
def process_pending_notifications_task(batch_size: int = 200) -> int:
    """Beat-scheduled: picks up any PENDING notification whose scheduled_at
    has arrived (initial sends and backed-off retries alike) and dispatches
    an individual send task per notification — keeping per-recipient
    independence intact.
    """
    with session_scope() as db:
        now = utcnow()
        due = db.query(Notification).filter(
            Notification.status == NotificationStatus.PENDING,
            Notification.scheduled_at <= now,
        ).limit(batch_size).all()
        ids = [n.id for n in due]

    for notification_id in ids:
        send_notification_task.delay(notification_id)
    return len(ids)

"""Notifications are queued per (user, appointment, type) so that patient and
doctor delivery are tracked and retried completely independently — one
recipient's failure never blocks or masks the other's success (req #46).
"""
from sqlalchemy.orm import Session

from datetime import timedelta

from app.models.base import NotificationStatus, NotificationType
from app.models.identity import Doctor, Patient, User
from app.models.messaging import Notification
from app.models.scheduling import Appointment
from app.utils.timeutils import utcnow


def queue_notification(db: Session, appointment: Appointment, notification_type: NotificationType, target_role: str, scheduled_at=None) -> Notification:
    if target_role == "PATIENT":
        patient = db.get(Patient, appointment.patient_id)
        user = db.get(User, patient.user_id)
    else:
        doctor = db.get(Doctor, appointment.doctor_id)
        user = db.get(User, doctor.user_id)

    notification = Notification(
        user_id=user.id,
        appointment_id=appointment.id,
        notification_type=notification_type,
        recipient=user.email,
        scheduled_at=scheduled_at or utcnow(),
    )
    db.add(notification)
    db.flush()
    return notification


def queue_booking_notifications(db: Session, appointment: Appointment) -> None:
    queue_notification(db, appointment, NotificationType.BOOKING_CONFIRMATION, "PATIENT")
    queue_notification(db, appointment, NotificationType.BOOKING_CONFIRMATION, "DOCTOR")
    queue_appointment_reminders(db, appointment)


def queue_appointment_reminders(db: Session, appointment: Appointment, hours_before: int = 24) -> None:
    """Schedules an upcoming-appointment REMINDER email for both patient and
    doctor, timed relative to the appointment's start_time (req: "booking
    confirmation, reminder, cancellation" — distinct from medication
    reminders). Only scheduled if that far-out time is still in the future;
    same-day bookings skip the reminder rather than firing immediately.
    """
    remind_at = appointment.start_time - timedelta(hours=hours_before)
    if remind_at <= utcnow():
        return
    queue_notification(db, appointment, NotificationType.REMINDER, "PATIENT", scheduled_at=remind_at)
    queue_notification(db, appointment, NotificationType.REMINDER, "DOCTOR", scheduled_at=remind_at)


def queue_cancellation_notifications(db: Session, appointment: Appointment) -> None:
    queue_notification(db, appointment, NotificationType.CANCELLATION, "PATIENT")
    queue_notification(db, appointment, NotificationType.CANCELLATION, "DOCTOR")
    _cancel_pending_reminders(db, appointment)


def queue_reschedule_notifications(db: Session, appointment: Appointment) -> None:
    queue_notification(db, appointment, NotificationType.RESCHEDULE, "PATIENT")
    queue_notification(db, appointment, NotificationType.RESCHEDULE, "DOCTOR")
    _cancel_pending_reminders(db, appointment)
    queue_appointment_reminders(db, appointment)


def _cancel_pending_reminders(db: Session, appointment: Appointment) -> None:
    """Removes not-yet-sent REMINDER notifications for this appointment so a
    reschedule or cancellation doesn't leave a stale reminder pointing at the
    old time (or firing at all, in the cancellation case)."""
    db.query(Notification).filter(
        Notification.appointment_id == appointment.id,
        Notification.notification_type == NotificationType.REMINDER,
        Notification.status == NotificationStatus.PENDING,
    ).delete(synchronize_session=False)

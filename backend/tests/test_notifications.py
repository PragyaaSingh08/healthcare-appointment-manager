from datetime import datetime, timedelta, timezone

from app.models.base import NotificationStatus, NotificationType
from app.models.messaging import Notification
from app.services import appointment_service, hold_service
from tests.factories import make_doctor, make_patient


def _book(db, doctor, patient, days_ahead=10):
    now = datetime.now(timezone.utc)
    delta = (doctor.working_hours[0].day_of_week - now.weekday()) % 7
    delta = delta if delta else 7
    start = (now + timedelta(days=max(delta, days_ahead))).replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=30)
    hold = hold_service.create_hold(db, doctor.id, patient.id, start, end)
    db.commit()
    return appointment_service.confirm_booking(db, hold, patient.id, "test symptoms"), start


def test_booking_schedules_reminder_for_both_parties(db):
    doctor = make_doctor(db, day_of_week=0)
    patient = make_patient(db, "reminder_patient@example.com")

    from app.services import notification_service

    appt, start = _book(db, doctor, patient)
    notification_service.queue_appointment_reminders(db, appt)
    db.commit()

    reminders = db.query(Notification).filter(
        Notification.appointment_id == appt.id, Notification.notification_type == NotificationType.REMINDER
    ).all()
    assert len(reminders) == 2  # patient + doctor
    for r in reminders:
        assert r.scheduled_at < start
        assert r.scheduled_at > datetime.now(timezone.utc)


def test_cancellation_removes_pending_reminders(db):
    from app.services import notification_service

    doctor = make_doctor(db, day_of_week=1)
    patient = make_patient(db, "cancel_reminder_patient@example.com")
    appt, _ = _book(db, doctor, patient)
    notification_service.queue_appointment_reminders(db, appt)
    db.commit()

    notification_service.queue_cancellation_notifications(db, appt)
    db.commit()

    remaining_reminders = db.query(Notification).filter(
        Notification.appointment_id == appt.id,
        Notification.notification_type == NotificationType.REMINDER,
        Notification.status == NotificationStatus.PENDING,
    ).count()
    assert remaining_reminders == 0

from datetime import datetime, timedelta, timezone

from app.models.base import AppointmentStatus, NotificationType
from app.models.messaging import Notification
from app.services import appointment_service, hold_service, leave_service
from tests.factories import make_doctor, make_patient


def test_leave_marks_affected_appointments_and_notifies_patient(db):
    doctor = make_doctor(db, day_of_week=1)  # Tuesday
    patient = make_patient(db, "leave_affected_patient@example.com")

    now = datetime.now(timezone.utc)
    days_ahead = (1 - now.weekday()) % 7 or 7
    target_day = (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
    start = target_day.replace(hour=10, minute=0)
    end = start + timedelta(minutes=30)

    hold = hold_service.create_hold(db, doctor.id, patient.id, start, end)
    db.commit()
    appointment = appointment_service.confirm_booking(db, hold, patient.id, "recurring headache")

    leave, affected = leave_service.add_leave(db, doctor.id, target_day.date(), "Doctor unavailable")

    assert len(affected) == 1
    assert affected[0].id == appointment.id

    db.refresh(appointment)
    # Historical record preserved, not deleted, just transitioned.
    assert appointment.status == AppointmentStatus.RESCHEDULE_REQUIRED

    notif = db.query(Notification).filter(
        Notification.appointment_id == appointment.id,
        Notification.notification_type == NotificationType.LEAVE_CONFLICT,
    ).first()
    assert notif is not None
    assert notif.recipient  # patient's email was resolved


def test_leave_blocks_new_slot_generation(db):
    from app.services import slot_service

    doctor = make_doctor(db, day_of_week=5)  # Saturday
    now = datetime.now(timezone.utc)
    days_ahead = (5 - now.weekday()) % 7 or 7
    target_day = (now + timedelta(days=days_ahead)).date()

    leave_service.add_leave(db, doctor.id, target_day, "Conference")

    slots = slot_service.get_available_slots(db, doctor.id, target_day)
    assert slots == []

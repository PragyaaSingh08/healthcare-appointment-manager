from datetime import datetime, timedelta, timezone

from app.models.base import HoldStatus
from app.services import appointment_service, hold_service, slot_service
from tests.factories import make_doctor, make_patient


def _next_matching_weekday(weekday: int) -> datetime:
    now = datetime.now(timezone.utc)
    days_ahead = (weekday - now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7  # always pick a future day for test stability
    return (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)


def test_available_slots_respects_working_hours(db):
    doctor = make_doctor(db, day_of_week=2)  # Wednesday
    target = _next_matching_weekday(2).date()

    slots = slot_service.get_available_slots(db, doctor.id, target)

    # 9am-5pm, 30-min slots = 16 slots
    assert len(slots) == 16
    assert slots[0].start.hour == 9
    assert slots[-1].end.hour == 17


def test_booked_slot_is_excluded(db):
    doctor = make_doctor(db, day_of_week=2)
    patient = make_patient(db, "booked_patient@example.com")
    target_day = _next_matching_weekday(2)
    start = target_day.replace(hour=10, minute=0)
    end = start + timedelta(minutes=30)

    hold = hold_service.create_hold(db, doctor.id, patient.id, start, end)
    db.commit()
    appointment_service.confirm_booking(db, hold, patient.id, "test symptoms")

    slots = slot_service.get_available_slots(db, doctor.id, target_day.date())
    assert all(s.start != start for s in slots)
    assert len(slots) == 15  # one fewer than the full day


def test_held_slot_is_excluded_while_active(db):
    doctor = make_doctor(db, day_of_week=2)
    patient = make_patient(db, "holder@example.com")
    target_day = _next_matching_weekday(2)
    start = target_day.replace(hour=11, minute=0)
    end = start + timedelta(minutes=30)

    hold_service.create_hold(db, doctor.id, patient.id, start, end)
    db.commit()

    slots = slot_service.get_available_slots(db, doctor.id, target_day.date())
    assert all(s.start != start for s in slots)


def test_doctor_on_leave_returns_no_slots(db):
    from app.services import leave_service

    doctor = make_doctor(db, day_of_week=2)
    target_day = _next_matching_weekday(2)

    leave_service.add_leave(db, doctor.id, target_day.date(), "Personal leave")

    slots = slot_service.get_available_slots(db, doctor.id, target_day.date())
    assert slots == []

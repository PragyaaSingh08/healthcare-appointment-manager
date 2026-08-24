"""Slot generation algorithm.

Complexity target: O(S + A + H)
  S = candidate slots for the day (working_hours_span / slot_duration)
  A = existing active appointments for that doctor on that day
  H = active (non-expired) slot holds for that doctor on that day

We deliberately fetch appointments and holds ONCE per request (2 queries,
each indexed on doctor_id + time range) rather than issuing a query per
candidate slot, which would be O(S) database round trips and is the
anti-pattern this design explicitly avoids.
"""
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import Doctor, DoctorLeave, DoctorWorkingHours
from app.models.scheduling import Appointment, SlotHold
from app.models.base import AppointmentStatus, HoldStatus
from app.utils.intervals import Interval, overlaps_any
from app.utils.timeutils import utcnow


def _day_bounds_utc(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def get_available_slots(db: Session, doctor_id: str, target_date: date) -> list[Interval]:
    doctor = db.get(Doctor, doctor_id)
    if not doctor or not doctor.is_active:
        return []

    # 1. Check leave (O(1) indexed lookup)
    on_leave = db.execute(
        select(DoctorLeave).where(DoctorLeave.doctor_id == doctor_id, DoctorLeave.leave_date == target_date)
    ).scalar_one_or_none()
    if on_leave:
        return []

    # 2. Working hours for that weekday
    day_of_week = target_date.weekday()
    working_hours = db.execute(
        select(DoctorWorkingHours).where(
            DoctorWorkingHours.doctor_id == doctor_id,
            DoctorWorkingHours.day_of_week == day_of_week,
            DoctorWorkingHours.is_active.is_(True),
        )
    ).scalars().all()
    if not working_hours:
        return []

    day_start_utc, day_end_utc = _day_bounds_utc(target_date)

    # 3. Fetch booked intervals ONCE (indexed on doctor_id + start_time)
    active_statuses = (AppointmentStatus.SCHEDULED, AppointmentStatus.RESCHEDULED)
    appointments = db.execute(
        select(Appointment.start_time, Appointment.end_time).where(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_(active_statuses),
            Appointment.start_time < day_end_utc,
            Appointment.end_time > day_start_utc,
        )
    ).all()

    # 4. Fetch active (non-expired) holds ONCE
    now = utcnow()
    holds = db.execute(
        select(SlotHold.start_time, SlotHold.end_time).where(
            SlotHold.doctor_id == doctor_id,
            SlotHold.status == HoldStatus.HELD,
            SlotHold.expires_at > now,
            SlotHold.start_time < day_end_utc,
            SlotHold.end_time > day_start_utc,
        )
    ).all()

    taken: list[Interval] = [Interval(s, e) for s, e in appointments] + [Interval(s, e) for s, e in holds]

    slot_minutes = doctor.slot_duration
    available: list[Interval] = []

    # 5. Generate candidate slots per working-hours window and filter in memory (O(S + len(taken)))
    for wh in working_hours:
        window_start = datetime.combine(target_date, wh.start_time, tzinfo=timezone.utc)
        window_end = datetime.combine(target_date, wh.end_time, tzinfo=timezone.utc)
        cursor = window_start
        step = timedelta(minutes=slot_minutes)
        while cursor + step <= window_end:
            candidate = Interval(cursor, cursor + step)
            if not overlaps_any(candidate, taken):
                available.append(candidate)
            cursor += step

    return available

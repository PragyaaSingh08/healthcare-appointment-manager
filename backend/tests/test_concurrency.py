"""Concurrency acceptance test (spec req #20/#91).

Fires N simultaneous booking confirmations at the same doctor+slot, each in
its own thread with its own DB session/connection (so this is real
concurrent DB access, not simulated). Asserts exactly one booking succeeds,
N-1 receive a 409 conflict, and the database ends up with exactly one
active appointment row for that slot.
"""
import threading
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.core.db import SessionLocal
from app.models.base import AppointmentStatus
from app.models.scheduling import Appointment
from app.services import appointment_service, hold_service
from tests.factories import make_doctor, make_patient


N_CONCURRENT = 12


def _attempt_booking(doctor_id: str, patient_id: str, start_time, end_time, results: list, index: int):
    """Runs in its own thread with its own DB session, simulating one
    independent client request end-to-end: hold -> confirm."""
    session = SessionLocal()
    try:
        hold = hold_service.create_hold(session, doctor_id, patient_id, start_time, end_time)
        session.commit()
        appt = appointment_service.confirm_booking(session, hold, patient_id, f"symptom text {index}")
        results[index] = ("SUCCESS", appt.id)
    except HTTPException as e:
        session.rollback()
        results[index] = ("CONFLICT", e.detail.get("code"))
    except Exception as e:
        session.rollback()
        results[index] = ("ERROR", str(e))
    finally:
        session.close()


def test_concurrent_booking_exactly_one_winner(db):
    doctor = make_doctor(db, day_of_week=datetime.now(timezone.utc).weekday())
    doctor_id = doctor.id

    # N distinct patients all trying to book the SAME slot.
    patient_ids = []
    for i in range(N_CONCURRENT):
        p = make_patient(db, email=f"concurrent_patient_{i}@example.com")
        patient_ids.append(p.id)

    # Pick a slot inside working hours, far enough in the future to be stable across runs.
    now = datetime.now(timezone.utc)
    start = now.replace(hour=10, minute=0, second=0, microsecond=0)
    if start <= now:
        start += timedelta(days=7)  # next week, same weekday as doctor's working hours
    end = start + timedelta(minutes=30)

    results = [None] * N_CONCURRENT
    threads = [
        threading.Thread(target=_attempt_booking, args=(doctor_id, patient_ids[i], start, end, results, i))
        for i in range(N_CONCURRENT)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    successes = [r for r in results if r and r[0] == "SUCCESS"]
    conflicts = [r for r in results if r and r[0] == "CONFLICT"]
    errors = [r for r in results if r and r[0] == "ERROR"]

    assert errors == [], f"Unexpected errors during concurrent booking: {errors}"
    assert len(successes) == 1, f"Expected exactly 1 successful booking, got {len(successes)}: {results}"
    assert len(conflicts) == N_CONCURRENT - 1, f"Expected {N_CONCURRENT - 1} conflicts, got {len(conflicts)}: {results}"

    # Verify the database itself has exactly one active appointment for this doctor+slot.
    verify_session = SessionLocal()
    try:
        active = verify_session.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.start_time == start,
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.RESCHEDULED]),
        ).all()
        assert len(active) == 1, f"Expected exactly 1 appointment row in DB, found {len(active)}"
    finally:
        verify_session.close()

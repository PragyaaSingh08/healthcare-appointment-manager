from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models.base import HoldStatus
from app.models.scheduling import SlotHold
from app.services import appointment_service, hold_service
from tests.factories import make_doctor, make_patient


def test_expired_hold_rejected_at_confirmation(db):
    doctor = make_doctor(db, day_of_week=3)
    patient = make_patient(db, "expiring_patient@example.com")

    start = (datetime.now(timezone.utc) + timedelta(days=7)).replace(hour=10, minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=30)

    hold = hold_service.create_hold(db, doctor.id, patient.id, start, end)
    # Force it into the past to simulate expiry without sleeping in the test.
    hold.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        hold_service.get_valid_hold(db, hold.id, patient.id)
    assert exc_info.value.detail["code"] == "HOLD_EXPIRED"

    # And the hold's own status should have been flipped to EXPIRED as a side effect.
    db.refresh(hold)
    assert hold.status == HoldStatus.EXPIRED


def test_cleanup_expired_holds_only_touches_expired_rows(db):
    doctor = make_doctor(db, day_of_week=3)
    patient = make_patient(db, "cleanup_patient@example.com")

    start = (datetime.now(timezone.utc) + timedelta(days=7)).replace(hour=9, minute=0, second=0, microsecond=0)
    active_hold = hold_service.create_hold(db, doctor.id, patient.id, start, start + timedelta(minutes=30))
    db.commit()

    expired_hold = hold_service.create_hold(db, doctor.id, patient.id, start + timedelta(hours=1), start + timedelta(hours=1, minutes=30))
    expired_hold.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    cleaned = hold_service.cleanup_expired_holds(db)
    assert cleaned == 1

    db.refresh(active_hold)
    db.refresh(expired_hold)
    assert active_hold.status == HoldStatus.HELD
    assert expired_hold.status == HoldStatus.EXPIRED


def test_hold_owned_by_other_patient_rejected(db):
    doctor = make_doctor(db, day_of_week=4)
    owner = make_patient(db, "owner@example.com")
    intruder = make_patient(db, "intruder@example.com")

    start = (datetime.now(timezone.utc) + timedelta(days=7)).replace(hour=9, minute=0, second=0, microsecond=0)
    hold = hold_service.create_hold(db, doctor.id, owner.id, start, start + timedelta(minutes=30))
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        hold_service.get_valid_hold(db, hold.id, intruder.id)
    assert exc_info.value.detail["code"] == "HOLD_NOT_OWNED"

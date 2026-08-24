"""Slot hold lifecycle: AVAILABLE -> HELD -> CONFIRMED (or EXPIRED/RELEASED).

Holds are a UX optimization to reduce booking collisions, NOT the source of
booking correctness. Correctness is enforced at confirmation time by
re-validating against the appointments table inside a transaction (see
appointment_service.confirm_booking). This module never assumes a hold is
still valid without re-checking expires_at at the moment of use.
"""
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.base import HoldStatus
from app.models.scheduling import SlotHold
from app.utils.intervals import Interval, overlaps
from app.utils.timeutils import utcnow

settings = get_settings()


def create_hold(db: Session, doctor_id: str, patient_id: str, start_time, end_time) -> SlotHold:
    now = utcnow()

    # Release any of this patient's own stale/expired holds first (best effort tidy-up).
    _expire_stale_holds_for_doctor(db, doctor_id)

    # Check for a conflicting ACTIVE hold from another patient on this exact slot.
    conflicting = db.execute(
        select(SlotHold).where(
            SlotHold.doctor_id == doctor_id,
            SlotHold.status == HoldStatus.HELD,
            SlotHold.expires_at > now,
            SlotHold.start_time < end_time,
            SlotHold.end_time > start_time,
        )
    ).scalars().first()
    if conflicting and conflicting.patient_id != patient_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "SLOT_CURRENTLY_HELD", "message": "This slot is currently held by another patient."},
        )

    hold = SlotHold(
        doctor_id=doctor_id,
        patient_id=patient_id,
        start_time=start_time,
        end_time=end_time,
        status=HoldStatus.HELD,
        held_at=now,
        expires_at=now + timedelta(seconds=settings.SLOT_HOLD_DURATION_SECONDS),
    )
    db.add(hold)
    db.flush()
    return hold


def _expire_stale_holds_for_doctor(db: Session, doctor_id: str) -> None:
    """Inline expiry check performed during booking so stale holds can never
    block a slot indefinitely, even if the background cleanup worker is
    delayed or down. Bounded by the (doctor_id, expires_at) index.
    """
    now = utcnow()
    db.execute(
        update(SlotHold)
        .where(SlotHold.doctor_id == doctor_id, SlotHold.status == HoldStatus.HELD, SlotHold.expires_at <= now)
        .values(status=HoldStatus.EXPIRED)
    )


def get_valid_hold(db: Session, hold_id: str, patient_id: str) -> SlotHold:
    hold = db.get(SlotHold, hold_id)
    if not hold:
        raise HTTPException(status_code=404, detail={"code": "HOLD_NOT_FOUND", "message": "Hold not found."})
    if hold.patient_id != patient_id:
        raise HTTPException(status_code=403, detail={"code": "HOLD_NOT_OWNED", "message": "This hold does not belong to you."})
    if hold.status != HoldStatus.HELD:
        raise HTTPException(status_code=409, detail={"code": "HOLD_NOT_ACTIVE", "message": f"Hold is {hold.status}."})
    if hold.expires_at <= utcnow():
        hold.status = HoldStatus.EXPIRED
        db.flush()
        raise HTTPException(status_code=409, detail={"code": "HOLD_EXPIRED", "message": "This slot hold has expired."})
    return hold


def release_hold(db: Session, hold_id: str, patient_id: str) -> None:
    hold = db.get(SlotHold, hold_id)
    if not hold or hold.patient_id != patient_id:
        raise HTTPException(status_code=404, detail={"code": "HOLD_NOT_FOUND", "message": "Hold not found."})
    if hold.status == HoldStatus.HELD:
        hold.status = HoldStatus.RELEASED
        db.flush()


def cleanup_expired_holds(db: Session, batch_size: int = 500) -> int:
    """Used by the background HoldCleanupWorker. Uses the (expires_at, status)
    index so it only touches expired HELD rows, never a full table scan."""
    now = utcnow()
    ids = db.execute(
        select(SlotHold.id).where(SlotHold.status == HoldStatus.HELD, SlotHold.expires_at <= now).limit(batch_size)
    ).scalars().all()
    if not ids:
        return 0
    db.execute(update(SlotHold).where(SlotHold.id.in_(ids)).values(status=HoldStatus.EXPIRED))
    db.commit()
    return len(ids)

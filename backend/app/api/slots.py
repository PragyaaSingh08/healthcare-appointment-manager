from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_patient
from app.models.identity import Doctor, Patient
from app.schemas.api import HoldResponse, HoldSlotRequest
from app.services import hold_service
from app.utils.timeutils import ensure_utc

router = APIRouter(prefix="/api/slots", tags=["slots"])


@router.post("/hold", response_model=HoldResponse, status_code=201)
def hold_slot(payload: HoldSlotRequest, patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    start = ensure_utc(payload.start_time)
    # end_time is derived server-side from the doctor's slot_duration to
    # prevent a client from requesting an arbitrary-length hold.
    doctor = db.get(Doctor, payload.doctor_id)
    if not doctor or not doctor.is_active:
        raise HTTPException(status_code=404, detail={"code": "DOCTOR_NOT_FOUND", "message": "Doctor not found."})
    end = start + timedelta(minutes=doctor.slot_duration)

    hold = hold_service.create_hold(db, payload.doctor_id, patient.id, start, end)
    db.commit()
    return HoldResponse(id=hold.id, doctor_id=hold.doctor_id, start_time=hold.start_time, end_time=hold.end_time, status=hold.status.value, expires_at=hold.expires_at)


@router.delete("/{hold_id}", status_code=204)
def release_slot(hold_id: str, patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    hold_service.release_hold(db, hold_id, patient.id)
    db.commit()
    return None

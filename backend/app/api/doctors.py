from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models.base import UserRole
from app.models.identity import Doctor, DoctorWorkingHours, User
from app.schemas.api import CreateDoctorRequest, DoctorResponse, UpdateDoctorRequest
from app.services import slot_service
from app.services.auth_service import hash_password

router = APIRouter(prefix="/api/doctors", tags=["doctors"])


def _doctor_to_response(doctor: Doctor) -> DoctorResponse:
    return DoctorResponse(
        id=doctor.id,
        name=doctor.user.name,
        specialization=doctor.specialization,
        qualification=doctor.qualification,
        experience=doctor.experience,
        slot_duration=doctor.slot_duration,
        is_active=doctor.is_active,
    )


@router.get("", response_model=list[DoctorResponse])
def list_doctors(
    specialization: str | None = None,
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Doctor)
    if is_active is not None:
        query = query.filter(Doctor.is_active == is_active)
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
    doctors = query.offset((page - 1) * page_size).limit(page_size).all()
    return [_doctor_to_response(d) for d in doctors]


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(doctor_id: str, db: Session = Depends(get_db)):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail={"code": "DOCTOR_NOT_FOUND", "message": "Doctor not found."})
    return _doctor_to_response(doctor)


@router.get("/{doctor_id}/availability")
def get_availability(doctor_id: str, target_date: date = Query(..., alias="date"), db: Session = Depends(get_db)):
    slots = slot_service.get_available_slots(db, doctor_id, target_date)
    return {"date": target_date.isoformat(), "available_slots": [{"start": s.start.isoformat(), "end": s.end.isoformat()} for s in slots]}


@router.post("", response_model=DoctorResponse, status_code=201, dependencies=[Depends(require_role(UserRole.ADMIN))])
def create_doctor(payload: CreateDoctorRequest, db: Session = Depends(get_db)):
    user = User(name=payload.name, email=payload.email.lower(), password_hash=hash_password(payload.password), role=UserRole.DOCTOR)
    db.add(user)
    db.flush()

    doctor = Doctor(
        user_id=user.id,
        specialization=payload.specialization,
        qualification=payload.qualification,
        experience=payload.experience,
        slot_duration=payload.slot_duration,
    )
    db.add(doctor)
    db.flush()

    for wh in payload.working_hours:
        db.add(DoctorWorkingHours(doctor_id=doctor.id, day_of_week=wh.day_of_week, start_time=wh.start_time, end_time=wh.end_time))

    db.commit()
    db.refresh(doctor)
    return _doctor_to_response(doctor)


@router.put("/{doctor_id}", response_model=DoctorResponse, dependencies=[Depends(require_role(UserRole.ADMIN))])
def update_doctor(doctor_id: str, payload: UpdateDoctorRequest, db: Session = Depends(get_db)):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail={"code": "DOCTOR_NOT_FOUND", "message": "Doctor not found."})
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(doctor, field, value)
    db.commit()
    db.refresh(doctor)
    return _doctor_to_response(doctor)


@router.delete("/{doctor_id}", status_code=204, dependencies=[Depends(require_role(UserRole.ADMIN))])
def deactivate_doctor(doctor_id: str, db: Session = Depends(get_db)):
    doctor = db.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail={"code": "DOCTOR_NOT_FOUND", "message": "Doctor not found."})
    doctor.is_active = False
    db.commit()
    return None

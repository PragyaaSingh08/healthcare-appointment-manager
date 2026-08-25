from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models.base import UserRole
from app.schemas.api import LeaveRequest
from app.services import leave_service

router = APIRouter(prefix="/api/doctors", tags=["leave"], dependencies=[Depends(require_role(UserRole.ADMIN))])


@router.get("/{doctor_id}/leave")
def list_leaves(doctor_id: str, db: Session = Depends(get_db)):
    from app.models.identity import DoctorLeave

    leaves = db.query(DoctorLeave).filter(DoctorLeave.doctor_id == doctor_id).order_by(DoctorLeave.leave_date.asc()).all()
    return [{"id": l.id, "leave_date": l.leave_date.isoformat(), "reason": l.reason} for l in leaves]


@router.post("/{doctor_id}/leave", status_code=201)
def add_leave(doctor_id: str, payload: LeaveRequest, db: Session = Depends(get_db)):
    leave, affected = leave_service.add_leave(db, doctor_id, payload.leave_date, payload.reason)
    return {"id": leave.id, "leave_date": leave.leave_date.isoformat(), "affected_appointments": len(affected)}


@router.delete("/{doctor_id}/leave/{leave_id}", status_code=204)
def remove_leave(doctor_id: str, leave_id: str, db: Session = Depends(get_db)):
    leave_service.remove_leave(db, doctor_id, leave_id)
    return None

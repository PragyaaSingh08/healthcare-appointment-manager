from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.base import AppointmentStatus, NotificationType
from app.models.identity import DoctorLeave
from app.models.scheduling import Appointment
from app.services import notification_service
from app.utils.timeutils import utcnow


def add_leave(db: Session, doctor_id: str, leave_date: date, reason: str | None) -> tuple[DoctorLeave, list[Appointment]]:
    """Creates leave, finds affected appointments, marks them, and queues
    patient notifications. Historical/appointment records are never deleted —
    they are transitioned to RESCHEDULE_REQUIRED so the trail is preserved.
    """
    leave = DoctorLeave(doctor_id=doctor_id, leave_date=leave_date, reason=reason)
    db.add(leave)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "LEAVE_ALREADY_EXISTS", "message": "Leave already recorded for this date."})

    from datetime import datetime, timezone

    day_start = datetime.combine(leave_date, datetime.min.time(), tzinfo=timezone.utc)
    day_end = datetime.combine(leave_date, datetime.max.time(), tzinfo=timezone.utc)

    active_statuses = (AppointmentStatus.SCHEDULED, AppointmentStatus.RESCHEDULED)
    affected = db.execute(
        select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_(active_statuses),
            Appointment.start_time >= day_start,
            Appointment.start_time <= day_end,
        )
    ).scalars().all()

    for appt in affected:
        appt.status = AppointmentStatus.RESCHEDULE_REQUIRED
        db.flush()
        notification_service.queue_notification(
            db,
            appointment=appt,
            notification_type=NotificationType.LEAVE_CONFLICT,
            target_role="PATIENT",
        )

    db.commit()
    return leave, affected


def remove_leave(db: Session, doctor_id: str, leave_id: str) -> None:
    leave = db.get(DoctorLeave, leave_id)
    if not leave or leave.doctor_id != doctor_id:
        raise HTTPException(status_code=404, detail={"code": "LEAVE_NOT_FOUND", "message": "Leave record not found."})
    db.delete(leave)
    db.commit()

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_doctor, get_current_patient, get_current_user
from app.models.base import AppointmentStatus, UserRole
from app.models.identity import Doctor, Patient
from app.models.scheduling import Appointment
from app.schemas.api import AppointmentResponse, ConfirmHoldRequest, PreVisitSummaryResponse, RescheduleRequest
from app.services import ai_service, appointment_service, hold_service, notification_service

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


def _to_response(appt: Appointment) -> AppointmentResponse:
    return AppointmentResponse.model_validate(appt)


@router.post("/confirm/{hold_id}", response_model=AppointmentResponse, status_code=201)
def confirm_appointment(hold_id: str, payload: ConfirmHoldRequest, patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    hold = hold_service.get_valid_hold(db, hold_id, patient.id)
    appointment = appointment_service.confirm_booking(db, hold, patient.id, payload.symptoms)

    # Queue background work AFTER commit — never on the critical path.
    notification_service.queue_booking_notifications(db, appointment)
    db.commit()

    _enqueue_best_effort(appointment.id)

    # Pre-visit AI summary generation: in a full deployment this is also
    # deferred to a worker task; called directly here so the API response
    # (and this demo) can show the result without polling.
    ai_service.generate_pre_visit_summary(db, appointment, payload.symptoms)
    db.commit()

    return _to_response(appointment)


def _enqueue_best_effort(appointment_id: str) -> None:
    """Enqueues async notification/calendar sync jobs. Best-effort: if the
    broker (Redis) isn't running — e.g. running the API standalone for a
    quick demo — this must never fail the booking request itself.
    """
    try:
        from app.workers.email_worker import process_pending_notifications_task
        from app.workers.calendar_worker import sync_calendar_event_task

        process_pending_notifications_task.delay()
        sync_calendar_event_task.delay(appointment_id, "PATIENT", "create")
        sync_calendar_event_task.delay(appointment_id, "DOCTOR", "create")
    except Exception:
        logging.getLogger("appointments_api").warning("Background job broker unavailable; skipping async dispatch for %s", appointment_id)


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Appointment)
    if user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        query = query.filter(Appointment.patient_id == patient.id)
    elif user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        query = query.filter(Appointment.doctor_id == doctor.id)
    # ADMIN sees all appointments.
    appts = query.order_by(Appointment.start_time.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return [_to_response(a) for a in appts]


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(appointment_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    appt = _get_authorized_appointment(db, appointment_id, user)
    return _to_response(appt)


def _get_authorized_appointment(db: Session, appointment_id: str, user) -> Appointment:
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail={"code": "APPOINTMENT_NOT_FOUND", "message": "Appointment not found."})
    if user.role == UserRole.PATIENT:
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not patient or appt.patient_id != patient.id:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Not your appointment."})
    elif user.role == UserRole.DOCTOR:
        doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if not doctor or appt.doctor_id != doctor.id:
            raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Not your appointment."})
    return appt


@router.put("/{appointment_id}/reschedule", response_model=AppointmentResponse)
def reschedule(appointment_id: str, payload: RescheduleRequest, patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    appt = db.get(Appointment, appointment_id)
    if not appt or appt.patient_id != patient.id:
        raise HTTPException(status_code=404, detail={"code": "APPOINTMENT_NOT_FOUND", "message": "Appointment not found."})

    hold = hold_service.get_valid_hold(db, payload.hold_id, patient.id)
    if hold.doctor_id != appt.doctor_id:
        raise HTTPException(status_code=400, detail={"code": "DOCTOR_MISMATCH", "message": "Reschedule hold must be for the same doctor."})

    appointment_service.reschedule_appointment(db, appt, hold.start_time, hold.end_time)
    notification_service.queue_reschedule_notifications(db, appt)
    db.commit()
    _enqueue_calendar_update(appt.id, "update")
    return _to_response(appt)


@router.post("/{appointment_id}/cancel", response_model=AppointmentResponse)
def cancel(appointment_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    appt = _get_authorized_appointment(db, appointment_id, user)
    appointment_service.cancel_appointment(db, appt)
    notification_service.queue_cancellation_notifications(db, appt)
    db.commit()
    _enqueue_calendar_update(appt.id, "delete")
    return _to_response(appt)


def _enqueue_calendar_update(appointment_id: str, action: str) -> None:
    try:
        from app.workers.calendar_worker import sync_calendar_event_task

        sync_calendar_event_task.delay(appointment_id, "PATIENT", action)
        sync_calendar_event_task.delay(appointment_id, "DOCTOR", action)
    except Exception:
        logging.getLogger("appointments_api").warning("Background job broker unavailable; skipping calendar %s for %s", action, appointment_id)


@router.get("/{appointment_id}/previsit-summary", response_model=PreVisitSummaryResponse)
def get_previsit_summary(appointment_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    appt = _get_authorized_appointment(db, appointment_id, user)
    summary = appt.pre_visit_summary
    if not summary:
        raise HTTPException(status_code=404, detail={"code": "SUMMARY_NOT_FOUND", "message": "Pre-visit summary not generated yet."})
    import json

    return PreVisitSummaryResponse(
        urgency=summary.urgency,
        chief_complaint=summary.chief_complaint,
        suggested_questions=json.loads(summary.suggested_questions) if summary.suggested_questions else None,
        status=summary.status,
    )

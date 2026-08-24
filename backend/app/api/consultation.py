import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_doctor, get_current_user
from app.models.base import AppointmentStatus, UserRole
from app.models.identity import Doctor, Patient
from app.models.scheduling import Appointment, ClinicalNote, Prescription
from app.schemas.api import ClinicalNoteRequest, PostVisitSummaryResponse, PrescriptionRequest
from app.services import ai_service, rag_service, reminder_service

router = APIRouter(prefix="/api/appointments", tags=["consultation"])


def _get_doctor_appointment(db: Session, appointment_id: str, doctor: Doctor) -> Appointment:
    appt = db.get(Appointment, appointment_id)
    if not appt or appt.doctor_id != doctor.id:
        raise HTTPException(status_code=404, detail={"code": "APPOINTMENT_NOT_FOUND", "message": "Appointment not found."})
    return appt


def _get_authorized_appointment_for_read(db: Session, appointment_id: str, user) -> Appointment:
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


@router.get("/{appointment_id}/clinical-notes")
def get_clinical_notes(appointment_id: str, doctor: Doctor = Depends(get_current_doctor), db: Session = Depends(get_db)):
    """Lets the consultation form pre-fill with whatever was already saved,
    rather than always rendering blank (bug: previously there was no way to
    read back a note once written)."""
    appt = _get_doctor_appointment(db, appointment_id, doctor)
    if not appt.clinical_notes:
        return {"notes": None}
    return {"notes": appt.clinical_notes.notes}


@router.post("/{appointment_id}/clinical-notes", status_code=200)
def add_clinical_notes(appointment_id: str, payload: ClinicalNoteRequest, doctor: Doctor = Depends(get_current_doctor), db: Session = Depends(get_db)):
    """Upsert, not insert-only. `clinical_notes.appointment_id` is a unique
    column, so a second save on the same appointment used to raise an
    unhandled IntegrityError (confirmed via a direct DB reproduction) — this
    now updates the existing row instead of crashing.
    """
    appt = _get_doctor_appointment(db, appointment_id, doctor)
    if appt.clinical_notes:
        appt.clinical_notes.notes = payload.notes
    else:
        db.add(ClinicalNote(appointment_id=appt.id, doctor_id=doctor.id, notes=payload.notes))
    db.commit()
    return {"status": "saved"}


@router.get("/{appointment_id}/prescriptions")
def get_prescriptions(appointment_id: str, doctor: Doctor = Depends(get_current_doctor), db: Session = Depends(get_db)):
    """Lets the consultation form pre-fill previously-entered medications."""
    appt = _get_doctor_appointment(db, appointment_id, doctor)
    return {
        "items": [
            {
                "medicine_name": rx.medicine_name,
                "dosage": rx.dosage,
                "frequency": rx.frequency,
                "duration": rx.duration,
                "instructions": rx.instructions,
            }
            for rx in appt.prescriptions
        ]
    }


@router.post("/{appointment_id}/prescription", status_code=201)
def add_prescription(appointment_id: str, payload: PrescriptionRequest, doctor: Doctor = Depends(get_current_doctor), db: Session = Depends(get_db)):
    appt = _get_doctor_appointment(db, appointment_id, doctor)

    if appt.status == AppointmentStatus.COMPLETED:
        # Prevents duplicate prescriptions, duplicate medication reminders,
        # and a re-triggered post-visit AI summary from a second accidental
        # submit on an already-completed visit.
        raise HTTPException(
            status_code=409,
            detail={"code": "VISIT_ALREADY_COMPLETED", "message": "This visit has already been completed and a prescription submitted."},
        )

    created = []
    for item in payload.items:
        rx = Prescription(
            appointment_id=appt.id,
            medicine_name=item.medicine_name,
            dosage=item.dosage,
            frequency=item.frequency,
            duration=item.duration,
            instructions=item.instructions,
        )
        db.add(rx)
        db.flush()
        reminder_service.generate_reminders(db, rx, appt.patient_id)
        created.append(rx)

    appt.status = AppointmentStatus.COMPLETED
    db.commit()

    # Post-visit AI summary generation, given notes + prescriptions now exist.
    if appt.clinical_notes:
        ai_service.generate_post_visit_summary(db, appt, appt.clinical_notes, created)
        db.commit()

    try:
        from app.workers.rag_worker import index_completed_visit_task

        index_completed_visit_task.delay(appt.id)
    except Exception:
        import logging

        logging.getLogger("consultation_api").warning("Background job broker unavailable; skipping RAG indexing for %s", appt.id)

    return {"status": "saved", "prescriptions": len(created)}


@router.get("/{appointment_id}/relevant-history")
def get_patient_history_for_consultation(appointment_id: str, doctor: Doctor = Depends(get_current_doctor), db: Session = Depends(get_db)):
    """Doctor-authorized patient-history retrieval, scoped to a specific
    appointment. Authorization chain: doctor authentication -> appointment
    ownership check -> patient_id derived from that appointment (never taken
    from the client) -> RAG retrieval filtered to that patient_id only.
    """
    appt = _get_doctor_appointment(db, appointment_id, doctor)
    symptom_text = appt.symptoms.symptom_text if appt.symptoms else "general checkup"
    chunks = rag_service.retrieve_relevant_history(appt.patient_id, symptom_text)
    return {"context": rag_service.build_compact_context(chunks)}


@router.get("/{appointment_id}/postvisit-summary", response_model=PostVisitSummaryResponse)
def get_postvisit_summary(appointment_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """NOTE: this route's decorator was accidentally dropped in a prior edit
    (when the relevant-history endpoint above was inserted), which meant this
    endpoint silently stopped being registered at all — every call would have
    404'd. Restored here and covered by a regression test."""
    appt = _get_authorized_appointment_for_read(db, appointment_id, user)

    if not appt.post_visit_summary:
        raise HTTPException(status_code=404, detail={"code": "SUMMARY_NOT_FOUND", "message": "Post-visit summary not available yet."})
    summary = appt.post_visit_summary
    return PostVisitSummaryResponse(
        summary=summary.summary,
        medication_schedule=json.loads(summary.medication_schedule) if summary.medication_schedule else None,
        follow_up_steps=json.loads(summary.follow_up_steps) if summary.follow_up_steps else None,
        status=summary.status,
    )

"""CalendarWorker — creates/updates/deletes Google Calendar events for both
patient and doctor independently (req #48-#52). A failure for one party
never blocks or rolls back the other, and never rolls back the appointment.
"""
import logging

from app.core.db import session_scope
from app.models.base import CalendarEventStatus
from app.models.identity import Doctor, Patient, User
from app.models.messaging import CalendarEvent, GoogleOAuthToken
from app.models.scheduling import Appointment
from app.services.calendar_service import CalendarPermanentError, CalendarTransientError, create_event, delete_event, update_event
from app.workers.celery_app import celery_app

logger = logging.getLogger("calendar_worker")


def _resolve_user_for_role(db, appointment: Appointment, role: str) -> User:
    if role == "PATIENT":
        patient = db.get(Patient, appointment.patient_id)
        return db.get(User, patient.user_id)
    doctor = db.get(Doctor, appointment.doctor_id)
    return db.get(User, doctor.user_id)


@celery_app.task(name="app.workers.calendar_worker.sync_calendar_event_task", bind=True)
def sync_calendar_event_task(self, appointment_id: str, role: str, action: str = "create") -> None:
    """action: create | update | delete. Idempotent by appointment_id+role+provider."""
    with session_scope() as db:
        appointment = db.get(Appointment, appointment_id)
        if not appointment:
            return
        user = _resolve_user_for_role(db, appointment, role)

        token = db.query(GoogleOAuthToken).filter(GoogleOAuthToken.user_id == user.id).first()
        if not token:
            return

        event = db.query(CalendarEvent).filter(
            CalendarEvent.appointment_id == appointment_id, CalendarEvent.user_id == user.id
        ).first()
        if not event:
            event = CalendarEvent(appointment_id=appointment_id, user_id=user.id, role=role, status=CalendarEventStatus.PENDING)
            db.add(event)
            db.flush()

        doctor = db.get(Doctor, appointment.doctor_id)
        title = f"Appointment: {doctor.specialization} consultation"
        duration_minutes = int((appointment.end_time - appointment.start_time).total_seconds() // 60)
        description = f"Appointment reference {appointment.booking_reference}. Duration {duration_minutes} minutes."

        try:
            if action == "delete":
                if event.external_event_id:
                    delete_event(token, event.external_event_id)
                event.status = CalendarEventStatus.DELETED
            elif action == "update" and event.external_event_id:
                update_event(token, event.external_event_id, appointment.start_time, appointment.end_time)
                event.status = CalendarEventStatus.SYNCED
            else:
                external_id = create_event(token, title, description, appointment.start_time, appointment.end_time)
                event.external_event_id = external_id
                event.status = CalendarEventStatus.SYNCED
        except CalendarPermanentError as e:
            event.status = CalendarEventStatus.FAILED
            event.last_error = str(e)
            logger.error("Permanent calendar failure for appointment %s role %s: %s", appointment_id, role, e)
        except CalendarTransientError as e:
            event.status = CalendarEventStatus.SYNC_PENDING
            event.last_error = str(e)
            logger.warning("Transient calendar failure for appointment %s role %s: %s", appointment_id, role, e)


@celery_app.task(name="app.workers.calendar_worker.sync_pending_calendar_events_task")
def sync_pending_calendar_events_task(batch_size: int = 100) -> int:
    with session_scope() as db:
        pending = db.query(CalendarEvent).filter(CalendarEvent.status == CalendarEventStatus.SYNC_PENDING).limit(batch_size).all()
        jobs = [(e.appointment_id, e.role) for e in pending]

    for appointment_id, role in jobs:
        sync_calendar_event_task.delay(appointment_id, role, "create")
    return len(jobs)

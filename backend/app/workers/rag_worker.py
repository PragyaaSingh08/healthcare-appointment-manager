"""RAGIndexWorker indexes clinical notes, prescriptions, and post-visit
summaries into ChromaDB after a visit completes. Runs asynchronously so
RAG indexing never blocks appointment completion (req #39).
"""
import json
import logging

from app.core.db import session_scope
from app.models.messaging import PatientHistoryDocument
from app.models.scheduling import Appointment
from app.services import rag_service
from app.workers.celery_app import celery_app

logger = logging.getLogger("rag_worker")


@celery_app.task(name="app.workers.rag_worker.index_completed_visit_task", bind=True)
def index_completed_visit_task(self, appointment_id: str) -> None:
    with session_scope() as db:
        appointment = db.get(Appointment, appointment_id)
        if not appointment:
            return

        chunks = []
        if appointment.symptoms:
            chunks.append(("symptom", appointment.symptoms.symptom_text))
        if appointment.clinical_notes:
            chunks.append(("clinical_note", appointment.clinical_notes.notes))
        for rx in appointment.prescriptions:
            chunks.append(("prescription", f"{rx.medicine_name} {rx.dosage} {rx.frequency} {rx.duration or ''}"))
        if appointment.post_visit_summary and appointment.post_visit_summary.summary:
            chunks.append(("summary", appointment.post_visit_summary.summary))

        for doc_type, text in chunks:
            doc = PatientHistoryDocument(
                patient_id=appointment.patient_id,
                appointment_id=appointment.id,
                document_type=doc_type,
                source_text=text,
                doc_metadata=json.dumps({"doctor_id": appointment.doctor_id}),
            )
            db.add(doc)
            db.flush()
            try:
                rag_service.index_document(
                    document_id=doc.id,
                    patient_id=appointment.patient_id,
                    appointment_id=appointment.id,
                    document_type=doc_type,
                    text=text,
                    doctor_id=appointment.doctor_id,
                    date=appointment.start_time.date().isoformat(),
                )
            except Exception as e:
                logger.warning("RAG indexing failed for doc %s (appointment %s): %s", doc.id, appointment_id, e)

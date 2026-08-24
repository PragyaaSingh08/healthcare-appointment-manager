"""AIService sits between business logic and GroqService. Its central job is
graceful degradation (req #33): if Groq fails for ANY reason, the appointment
and symptoms remain valid, we mark AI status = FAILED, and we NEVER fabricate
a response. Callers should always check the returned status.
"""
import json
import logging

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.base import AIStatus
from app.models.scheduling import Appointment, ClinicalNote, PostVisitAISummary, Prescription, PreVisitAISummary
from app.prompts.clinical_prompts import (
    POST_VISIT_SYSTEM_PROMPT,
    PRE_VISIT_SYSTEM_PROMPT,
    build_post_visit_user_prompt,
    build_pre_visit_user_prompt,
)
from app.schemas.ai import PostVisitAIResult, PreVisitAIResult
from app.services.groq_service import GroqInvalidJSONError, GroqPermanentError, GroqTransientError, groq_service
from app.core.config import get_settings

logger = logging.getLogger("ai_service")
settings = get_settings()


def generate_pre_visit_summary(db: Session, appointment: Appointment, symptom_text: str, history_context: str | None = None) -> PreVisitAISummary:
    row = PreVisitAISummary(appointment_id=appointment.id, status=AIStatus.PENDING.value, model_name=settings.GROQ_MODEL)
    db.add(row)
    db.flush()

    user_prompt = build_pre_visit_user_prompt(symptom_text, history_context)
    try:
        raw = groq_service.complete_json(PRE_VISIT_SYSTEM_PROMPT, user_prompt)
        result = PreVisitAIResult.model_validate(raw)
        row.urgency = result.urgency
        row.chief_complaint = result.chief_complaint
        row.suggested_questions = json.dumps(result.suggested_questions)
        row.raw_response = json.dumps(raw)
        row.status = AIStatus.SUCCESS.value
    except (GroqTransientError, GroqPermanentError, GroqInvalidJSONError, ValidationError) as e:
        logger.warning("Pre-visit AI generation failed for appointment %s: %s", appointment.id, e)
        row.status = AIStatus.FAILED.value
        row.raw_response = json.dumps({"error": str(e)})

    db.flush()
    return row


def generate_post_visit_summary(db: Session, appointment: Appointment, clinical_note: ClinicalNote, prescriptions: list[Prescription]) -> PostVisitAISummary:
    row = PostVisitAISummary(appointment_id=appointment.id, status=AIStatus.PENDING.value, model_name=settings.GROQ_MODEL)
    db.add(row)
    db.flush()

    prescriptions_text = "\n".join(
        f"- {p.medicine_name} {p.dosage}, {p.frequency}"
        + (f", {p.duration}" if p.duration else "")
        + (f" ({p.instructions})" if p.instructions else "")
        for p in prescriptions
    ) or "No medications prescribed."

    user_prompt = build_post_visit_user_prompt(clinical_note.notes, prescriptions_text)
    try:
        raw = groq_service.complete_json(POST_VISIT_SYSTEM_PROMPT, user_prompt)
        result = PostVisitAIResult.model_validate(raw)
        row.summary = result.summary
        row.medication_schedule = json.dumps([m.model_dump() for m in result.medication_schedule])
        row.follow_up_steps = json.dumps(result.follow_up_steps)
        row.status = AIStatus.SUCCESS.value
    except (GroqTransientError, GroqPermanentError, GroqInvalidJSONError, ValidationError) as e:
        logger.warning("Post-visit AI generation failed for appointment %s: %s", appointment.id, e)
        row.status = AIStatus.FAILED.value

    db.flush()
    return row

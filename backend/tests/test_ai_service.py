from unittest.mock import patch

from app.models.base import AIStatus
from app.services import ai_service
from app.services.groq_service import GroqTransientError
from tests.factories import make_doctor, make_patient
from datetime import datetime, timedelta, timezone

from app.services import appointment_service, hold_service


def _make_confirmed_appointment(db):
    doctor = make_doctor(db, day_of_week=0)
    patient = make_patient(db, "ai_test_patient@example.com")
    now = datetime.now(timezone.utc)
    days_ahead = (0 - now.weekday()) % 7 or 7
    start = (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=30)
    hold = hold_service.create_hold(db, doctor.id, patient.id, start, end)
    db.commit()
    return appointment_service.confirm_booking(db, hold, patient.id, "chest tightness for 2 days")


def test_pre_visit_ai_success_produces_structured_result(db):
    appointment = _make_confirmed_appointment(db)

    fake_response = {
        "urgency": "Medium",
        "chief_complaint": "Chest tightness for 2 days",
        "suggested_questions": ["When did it start?", "Any shortness of breath?", "Any prior heart conditions?"],
    }
    with patch("app.services.ai_service.groq_service.complete_json", return_value=fake_response):
        summary = ai_service.generate_pre_visit_summary(db, appointment, "chest tightness for 2 days")

    assert summary.status == AIStatus.SUCCESS.value
    assert summary.urgency == "Medium"


def test_pre_visit_ai_failure_does_not_break_appointment(db):
    appointment = _make_confirmed_appointment(db)

    with patch("app.services.ai_service.groq_service.complete_json", side_effect=GroqTransientError("timeout")):
        summary = ai_service.generate_pre_visit_summary(db, appointment, "chest tightness for 2 days")

    # AI failed gracefully...
    assert summary.status == AIStatus.FAILED.value

    # ...but the appointment and symptoms remain intact and valid.
    db.refresh(appointment)
    assert appointment.status.value in ("SCHEDULED",)
    assert appointment.symptoms is not None
    assert appointment.symptoms.symptom_text == "chest tightness for 2 days"


def test_pre_visit_ai_invalid_urgency_marked_failed_not_fabricated(db):
    appointment = _make_confirmed_appointment(db)

    bad_response = {"urgency": "Extremely Bad", "chief_complaint": "x", "suggested_questions": ["a", "b", "c"]}
    with patch("app.services.ai_service.groq_service.complete_json", return_value=bad_response):
        summary = ai_service.generate_pre_visit_summary(db, appointment, "chest tightness for 2 days")

    assert summary.status == AIStatus.FAILED.value
    assert summary.urgency is None  # never fabricated/coerced into a valid-looking value

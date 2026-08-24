from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models.base import AppointmentStatus
from app.services import appointment_service, hold_service
from tests.factories import make_doctor, make_patient

client = TestClient(app)


def _confirmed_appointment(db):
    doctor = make_doctor(db, day_of_week=2)
    patient = make_patient(db, "consult_bug_patient@example.com")
    now = datetime.now(timezone.utc)
    days_ahead = (2 - now.weekday()) % 7 or 7
    start = (now + timedelta(days=days_ahead)).replace(hour=9, minute=0, second=0, microsecond=0)
    end = start + timedelta(minutes=30)
    hold = hold_service.create_hold(db, doctor.id, patient.id, start, end)
    db.commit()
    appt = appointment_service.confirm_booking(db, hold, patient.id, "recurring migraines")
    return doctor, patient, appt


def test_saving_clinical_notes_twice_does_not_crash(db):
    """Regression test for the confirmed IntegrityError: previously, saving
    notes a second time on the same appointment raised an unhandled 500."""
    from app.services.auth_service import issue_token

    doctor, patient, appt = _confirmed_appointment(db)
    token = issue_token(doctor.user)
    headers = {"Authorization": f"Bearer {token}"}

    r1 = client.post(f"/api/appointments/{appt.id}/clinical-notes", json={"notes": "first draft"}, headers=headers)
    assert r1.status_code == 200

    # This second call used to raise IntegrityError (confirmed via direct DB repro).
    r2 = client.post(f"/api/appointments/{appt.id}/clinical-notes", json={"notes": "revised note"}, headers=headers)
    assert r2.status_code == 200

    r3 = client.get(f"/api/appointments/{appt.id}/clinical-notes", headers=headers)
    assert r3.status_code == 200
    assert r3.json()["notes"] == "revised note"


def test_prescriptions_are_readable_after_saving(db):
    from app.services.auth_service import issue_token

    doctor, patient, appt = _confirmed_appointment(db)
    token = issue_token(doctor.user)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(f"/api/appointments/{appt.id}/clinical-notes", json={"notes": "notes"}, headers=headers)
    save_resp = client.post(
        f"/api/appointments/{appt.id}/prescription",
        json={"items": [{"medicine_name": "Amoxicillin", "dosage": "500mg", "frequency": "TWICE_DAILY", "duration": "7 days"}]},
        headers=headers,
    )
    assert save_resp.status_code == 201

    read_resp = client.get(f"/api/appointments/{appt.id}/prescriptions", headers=headers)
    assert read_resp.status_code == 200
    items = read_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["medicine_name"] == "Amoxicillin"


def test_duplicate_prescription_submission_on_completed_visit_is_rejected(db):
    from app.services.auth_service import issue_token

    doctor, patient, appt = _confirmed_appointment(db)
    token = issue_token(doctor.user)
    headers = {"Authorization": f"Bearer {token}"}

    client.post(f"/api/appointments/{appt.id}/clinical-notes", json={"notes": "notes"}, headers=headers)
    first = client.post(
        f"/api/appointments/{appt.id}/prescription",
        json={"items": [{"medicine_name": "Ibuprofen", "dosage": "200mg", "frequency": "ONCE_DAILY"}]},
        headers=headers,
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/appointments/{appt.id}/prescription",
        json={"items": [{"medicine_name": "Ibuprofen", "dosage": "200mg", "frequency": "ONCE_DAILY"}]},
        headers=headers,
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "VISIT_ALREADY_COMPLETED"


def test_postvisit_summary_route_is_registered_and_reachable():
    """Regression test for the dropped route decorator: this endpoint was
    silently unregistered (would 404 for ANY appointment_id, even valid
    ones) because a prior edit deleted its @router.get(...) decorator."""
    from app.main import app as _app

    paths = [r.path for r in _app.routes if hasattr(r, "path")]
    assert "/api/appointments/{appointment_id}/postvisit-summary" in paths

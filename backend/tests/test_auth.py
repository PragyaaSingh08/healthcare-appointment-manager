import pytest
from fastapi import HTTPException

from app.models.base import UserRole
from app.services import auth_service


def test_register_and_login(db):
    user = auth_service.register_patient(db, "Jane Doe", "jane@example.com", "supersecret1")
    assert user.role == UserRole.PATIENT
    assert user.patient is not None

    logged_in = auth_service.authenticate(db, "jane@example.com", "supersecret1")
    assert logged_in.id == user.id

    token = auth_service.issue_token(logged_in)
    assert isinstance(token, str) and len(token) > 10


def test_duplicate_email_rejected(db):
    auth_service.register_patient(db, "Jane Doe", "dupe@example.com", "supersecret1")
    with pytest.raises(HTTPException) as exc_info:
        auth_service.register_patient(db, "Jane Doe 2", "dupe@example.com", "supersecret2")
    assert exc_info.value.detail["code"] == "EMAIL_ALREADY_REGISTERED"


def test_wrong_password_rejected(db):
    auth_service.register_patient(db, "Jane Doe", "wrongpw@example.com", "supersecret1")
    with pytest.raises(HTTPException) as exc_info:
        auth_service.authenticate(db, "wrongpw@example.com", "wrongpassword")
    assert exc_info.value.detail["code"] == "INVALID_CREDENTIALS"

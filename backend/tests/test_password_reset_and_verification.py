from datetime import timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.models.auth_tokens import EmailVerificationToken, PasswordResetToken
from app.services import auth_service
from app.utils.timeutils import utcnow

client = TestClient(app)


def test_registration_creates_unverified_user_with_verification_token(db):
    user = auth_service.register_patient(db, "Verify Me", "verify_flow@example.com", "supersecret1")
    assert user.is_email_verified is False

    token_row = db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user.id).first()
    assert token_row is not None
    assert token_row.used_at is None
    assert token_row.expires_at > utcnow()


def test_verify_email_with_valid_token_marks_user_verified(db):
    user = auth_service.register_patient(db, "Verify Me Two", "verify_flow2@example.com", "supersecret1")

    # Grab a fresh token the way a real email link would carry it: generate
    # and hash it ourselves here since we can't intercept the actual email.
    from app.core.security import generate_raw_token, hash_token

    raw = generate_raw_token()
    token_row = db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user.id).first()
    token_row.token_hash = hash_token(raw)
    db.commit()

    auth_service.verify_email(db, raw)
    db.refresh(user)
    assert user.is_email_verified is True
    db.refresh(token_row)
    assert token_row.used_at is not None


def test_verify_email_rejects_invalid_token(db):
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        auth_service.verify_email(db, "not-a-real-token")
    assert exc_info.value.detail["code"] == "INVALID_OR_EXPIRED_TOKEN"


def test_verify_email_rejects_expired_token(db):
    import pytest
    from fastapi import HTTPException
    from app.core.security import generate_raw_token, hash_token

    user = auth_service.register_patient(db, "Expiry Test", "verify_expiry@example.com", "supersecret1")
    raw = generate_raw_token()
    db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user.id).delete()
    expired = EmailVerificationToken(user_id=user.id, token_hash=hash_token(raw), expires_at=utcnow() - timedelta(minutes=1))
    db.add(expired)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        auth_service.verify_email(db, raw)
    assert exc_info.value.detail["code"] == "INVALID_OR_EXPIRED_TOKEN"


def test_verify_email_token_cannot_be_reused(db):
    import pytest
    from fastapi import HTTPException
    from app.core.security import generate_raw_token, hash_token

    user = auth_service.register_patient(db, "Reuse Test", "verify_reuse@example.com", "supersecret1")
    raw = generate_raw_token()
    token_row = db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user.id).first()
    token_row.token_hash = hash_token(raw)
    db.commit()

    auth_service.verify_email(db, raw)  # first use succeeds

    with pytest.raises(HTTPException) as exc_info:
        auth_service.verify_email(db, raw)  # second use must fail
    assert exc_info.value.detail["code"] == "INVALID_OR_EXPIRED_TOKEN"


def test_forgot_password_creates_token_for_existing_user(db):
    auth_service.register_patient(db, "Reset Me", "reset_flow@example.com", "oldpassword1")
    auth_service.request_password_reset(db, "reset_flow@example.com")

    from app.models.identity import User

    user = db.query(User).filter(User.email == "reset_flow@example.com").first()
    token_row = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).first()
    assert token_row is not None
    assert token_row.used_at is None


def test_forgot_password_nonexistent_email_does_not_error_or_leak(db):
    """Must behave identically (no exception, no token created) for an
    unregistered email — this is what prevents account enumeration."""
    before_count = db.query(PasswordResetToken).count()
    auth_service.request_password_reset(db, "definitely_not_registered@example.com")
    after_count = db.query(PasswordResetToken).count()
    assert before_count == after_count


def test_reset_password_with_valid_token_changes_password_and_allows_login(db):
    user = auth_service.register_patient(db, "Reset Two", "reset_flow2@example.com", "oldpassword1")

    from app.core.security import generate_raw_token, hash_token

    raw = generate_raw_token()
    token_row = PasswordResetToken(user_id=user.id, token_hash=hash_token(raw), expires_at=utcnow() + timedelta(minutes=60))
    db.add(token_row)
    db.commit()

    auth_service.reset_password(db, raw, "brandnewpassword1")

    # Old password no longer works.
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        auth_service.authenticate(db, "reset_flow2@example.com", "oldpassword1")

    # New password works.
    logged_in = auth_service.authenticate(db, "reset_flow2@example.com", "brandnewpassword1")
    assert logged_in.id == user.id


def test_reset_password_token_cannot_be_reused(db):
    import pytest
    from fastapi import HTTPException
    from app.core.security import generate_raw_token, hash_token

    user = auth_service.register_patient(db, "Reset Three", "reset_flow3@example.com", "oldpassword1")
    raw = generate_raw_token()
    token_row = PasswordResetToken(user_id=user.id, token_hash=hash_token(raw), expires_at=utcnow() + timedelta(minutes=60))
    db.add(token_row)
    db.commit()

    auth_service.reset_password(db, raw, "firstnewpassword1")

    with pytest.raises(HTTPException) as exc_info:
        auth_service.reset_password(db, raw, "secondnewpassword1")
    assert exc_info.value.detail["code"] == "INVALID_OR_EXPIRED_TOKEN"


def test_reset_password_rejects_expired_token(db):
    import pytest
    from fastapi import HTTPException
    from app.core.security import generate_raw_token, hash_token

    user = auth_service.register_patient(db, "Reset Four", "reset_flow4@example.com", "oldpassword1")
    raw = generate_raw_token()
    token_row = PasswordResetToken(user_id=user.id, token_hash=hash_token(raw), expires_at=utcnow() - timedelta(minutes=1))
    db.add(token_row)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        auth_service.reset_password(db, raw, "newpassword1")
    assert exc_info.value.detail["code"] == "INVALID_OR_EXPIRED_TOKEN"


def test_forgot_password_http_endpoint_returns_generic_message_both_cases():
    r1 = client.post("/api/auth/forgot-password", json={"email": "totally_random_unregistered@example.com"})
    assert r1.status_code == 200
    msg1 = r1.json()["message"]

    client.post("/api/auth/register", json={"name": "HTTP Reset", "email": "http_reset_flow@example.com", "password": "password123"})
    r2 = client.post("/api/auth/forgot-password", json={"email": "http_reset_flow@example.com"})
    assert r2.status_code == 200
    msg2 = r2.json()["message"]

    assert msg1 == msg2  # identical response either way — no enumeration signal


def test_me_endpoint_reports_verification_status():
    reg = client.post("/api/auth/register", json={"name": "Me Check", "email": "me_check_verify@example.com", "password": "password123"})
    token = reg.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["is_email_verified"] is False

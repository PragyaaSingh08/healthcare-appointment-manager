import logging
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_raw_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.auth_tokens import EmailVerificationToken, PasswordResetToken
from app.models.base import UserRole
from app.models.identity import Doctor, Patient, User
from app.services.email_service import EmailPermanentError, EmailTransientError, get_email_provider
from app.utils.timeutils import utcnow

settings = get_settings()
logger = logging.getLogger("auth_service")


def register_patient(db: Session, name: str, email: str, password: str) -> User:
    user = User(name=name, email=email.lower().strip(), password_hash=hash_password(password), role=UserRole.PATIENT)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "EMAIL_ALREADY_REGISTERED", "message": "An account with this email already exists."})

    db.add(Patient(user_id=user.id))
    db.commit()

    # Best-effort: registration must succeed even if the verification email
    # fails to send (e.g. no EMAIL_API_KEY configured yet).
    try:
        send_verification_email(db, user)
    except Exception as e:
        logger.warning("Failed to send verification email to new user %s: %s", user.id, e)

    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password."})
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "ACCOUNT_DISABLED", "message": "This account has been disabled."})
    return user


def issue_token(user: User) -> str:
    return create_access_token(subject=user.id, role=user.role.value)


# ---------------------------------------------------------------------------
# Forgot / reset password
# ---------------------------------------------------------------------------

def request_password_reset(db: Session, email: str) -> None:
    """Always behaves the same way regardless of whether the email exists,
    so this endpoint can't be used to enumerate registered accounts. Any
    real work (token creation + email send) only happens if a matching,
    active user is found; either way the caller gets the same response.
    """
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user or not user.is_active:
        return

    raw_token = generate_raw_token()
    token_row = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
    )
    db.add(token_row)
    db.commit()

    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
    body = (
        f"We received a request to reset your password.\n\n"
        f"Reset your password: {reset_link}\n\n"
        f"This link expires in {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes. "
        f"If you didn't request this, you can safely ignore this email."
    )
    try:
        get_email_provider().send(user.email, "Reset your password", body)
    except (EmailTransientError, EmailPermanentError) as e:
        # The token still exists and is valid — logging this lets an admin
        # manually resend or investigate, without ever exposing account
        # existence back to the caller of this function.
        logger.warning("Failed to send password reset email to %s: %s", user.email, e)


def reset_password(db: Session, raw_token: str, new_password: str) -> None:
    token_hash = hash_token(raw_token)
    token_row = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()

    if not token_row or token_row.used_at is not None or token_row.expires_at <= utcnow():
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_OR_EXPIRED_TOKEN", "message": "This password reset link is invalid or has expired."},
        )

    user = db.get(User, token_row.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_OR_EXPIRED_TOKEN", "message": "This password reset link is invalid or has expired."},
        )

    user.password_hash = hash_password(new_password)
    token_row.used_at = utcnow()
    db.commit()


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------

def send_verification_email(db: Session, user: User) -> None:
    if user.is_email_verified:
        return

    raw_token = generate_raw_token()
    token_row = EmailVerificationToken(
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=utcnow() + timedelta(minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES),
    )
    db.add(token_row)
    db.commit()

    verify_link = f"{settings.FRONTEND_URL}/verify-email?token={raw_token}"
    body = (
        f"Please verify your email address to finish setting up your account.\n\n"
        f"Verify your email: {verify_link}\n\n"
        f"This link expires in {settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES // 60} hours."
    )
    get_email_provider().send(user.email, "Verify your email", body)


def verify_email(db: Session, raw_token: str) -> None:
    token_hash = hash_token(raw_token)
    token_row = db.query(EmailVerificationToken).filter(EmailVerificationToken.token_hash == token_hash).first()

    if not token_row or token_row.used_at is not None or token_row.expires_at <= utcnow():
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_OR_EXPIRED_TOKEN", "message": "This verification link is invalid or has expired."},
        )

    user = db.get(User, token_row.user_id)
    if not user:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_OR_EXPIRED_TOKEN", "message": "This verification link is invalid or has expired."},
        )

    user.is_email_verified = True
    token_row.used_at = utcnow()
    db.commit()

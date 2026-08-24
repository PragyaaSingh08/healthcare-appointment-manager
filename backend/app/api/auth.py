from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.identity import User
from app.schemas.api import (
    CurrentUserResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.register_patient(db, payload.name, payload.email, payload.password)
    token = auth_service.issue_token(user)
    return TokenResponse(access_token=token, role=user.role.value)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, payload.email, payload.password)
    token = auth_service.issue_token(user)
    return TokenResponse(access_token=token, role=user.role.value)


@router.post("/logout", status_code=204)
def logout():
    # Stateless JWT — logout is handled client-side by discarding the token.
    return None


@router.get("/me", response_model=CurrentUserResponse)
def me(user: User = Depends(get_current_user)):
    return CurrentUserResponse(id=user.id, name=user.name, email=user.email, role=user.role.value, is_email_verified=user.is_email_verified)


@router.post("/forgot-password", status_code=200)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    auth_service.request_password_reset(db, payload.email)
    # Deliberately identical response whether or not the email is registered
    # — this endpoint must never leak account existence.
    return {"message": "If an account with that email exists, a password reset link has been sent."}


@router.post("/reset-password", status_code=200)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password(db, payload.token, payload.new_password)
    return {"message": "Your password has been reset. You can now sign in."}


@router.post("/verify-email", status_code=200)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    auth_service.verify_email(db, payload.token)
    return {"message": "Your email has been verified."}


@router.post("/resend-verification", status_code=200)
def resend_verification(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.is_email_verified:
        return {"message": "Your email is already verified."}
    auth_service.send_verification_email(db, user)
    return {"message": "Verification email sent."}

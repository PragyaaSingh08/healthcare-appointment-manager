from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.base import UserRole
from app.models.identity import Doctor, Patient, User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "NOT_AUTHENTICATED", "message": "Authentication required."})
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token."})
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": "USER_NOT_FOUND", "message": "User not found or inactive."})
    # Role in the token is a convenience/perf hint; the source of truth for
    # authorization is always the user row loaded above (role never trusted
    # from client input on write paths).
    return user


def require_role(*roles: UserRole):
    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "FORBIDDEN", "message": "You do not have permission to perform this action."})
        return user

    return _checker


def get_current_patient(user: User = Depends(require_role(UserRole.PATIENT)), db: Session = Depends(get_db)) -> Patient:
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail={"code": "PATIENT_PROFILE_NOT_FOUND", "message": "Patient profile not found."})
    return patient


def get_current_doctor(user: User = Depends(require_role(UserRole.DOCTOR)), db: Session = Depends(get_db)) -> Doctor:
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail={"code": "DOCTOR_PROFILE_NOT_FOUND", "message": "Doctor profile not found."})
    return doctor

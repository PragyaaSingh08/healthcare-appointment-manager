from datetime import time

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.base import UserRole
from app.models.identity import Doctor, DoctorWorkingHours, Patient, User


def make_doctor(db: Session, day_of_week: int = 0, specialization: str = "General Medicine") -> Doctor:
    user = User(name="Dr. Test", email=f"doctor_{id(db)}_{day_of_week}@example.com", password_hash=hash_password("password123"), role=UserRole.DOCTOR)
    db.add(user)
    db.flush()
    doctor = Doctor(user_id=user.id, specialization=specialization, slot_duration=30)
    db.add(doctor)
    db.flush()
    db.add(DoctorWorkingHours(doctor_id=doctor.id, day_of_week=day_of_week, start_time=time(9, 0), end_time=time(17, 0)))
    db.commit()
    return doctor


def make_patient(db: Session, email: str) -> Patient:
    user = User(name="Test Patient", email=email, password_hash=hash_password("password123"), role=UserRole.PATIENT)
    db.add(user)
    db.flush()
    patient = Patient(user_id=user.id)
    db.add(patient)
    db.commit()
    return patient

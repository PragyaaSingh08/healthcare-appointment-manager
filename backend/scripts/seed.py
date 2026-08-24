"""Seed script — creates synthetic demo data ONLY. No real patient information.

Run with: ./venv/bin/python -m scripts.seed  (from the backend/ directory)
"""
import json
import sys
from datetime import date, datetime, time, timedelta, timezone

sys.path.insert(0, ".")

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.base import AppointmentStatus, UserRole
from app.models.identity import Doctor, DoctorWorkingHours, Patient, User
from app.models.scheduling import Appointment, ClinicalNote, Prescription, Symptom


def get_or_create_user(db, name, email, password, role):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return existing
    user = User(name=name, email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    db.flush()
    return user


def seed():
    db = SessionLocal()

    print("Seeding admin...")
    admin = get_or_create_user(db, "Clinic Admin", "admin@example.com", "AdminPass123!", UserRole.ADMIN)

    print("Seeding doctors...")
    doctor_specs = [
        ("Dr. Meera Rao", "meera.rao@example.com", "General Medicine", "MBBS, MD", 12),
        ("Dr. Alex Chen", "alex.chen@example.com", "Dermatology", "MBBS, MD (Derm)", 8),
        ("Dr. Priya Nair", "priya.nair@example.com", "Cardiology", "MBBS, DM (Cardiology)", 15),
    ]
    doctors = []
    for name, email, spec, qual, exp in doctor_specs:
        user = get_or_create_user(db, name, email, "DoctorPass123!", UserRole.DOCTOR)
        doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if not doctor:
            doctor = Doctor(user_id=user.id, specialization=spec, qualification=qual, experience=exp, slot_duration=30)
            db.add(doctor)
            db.flush()
            for day in range(5):  # Mon-Fri
                db.add(DoctorWorkingHours(doctor_id=doctor.id, day_of_week=day, start_time=time(9, 0), end_time=time(17, 0)))
        doctors.append(doctor)

    print("Seeding patients...")
    patient_specs = [
        ("Jordan Blake", "jordan.blake@example.com"),
        ("Sam Rivera", "sam.rivera@example.com"),
        ("Taylor Kim", "taylor.kim@example.com"),
    ]
    patients = []
    for name, email in patient_specs:
        user = get_or_create_user(db, name, email, "PatientPass123!", UserRole.PATIENT)
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not patient:
            patient = Patient(user_id=user.id, gender="unspecified")
            db.add(patient)
            db.flush()
        patients.append(patient)

    db.commit()

    print("Seeding a synthetic completed visit for RAG testing...")
    existing_appt = db.query(Appointment).filter(Appointment.patient_id == patients[0].id).first()
    if not existing_appt:
        past_start = datetime.now(timezone.utc) - timedelta(days=30)
        appt = Appointment(
            patient_id=patients[0].id,
            doctor_id=doctors[0].id,
            start_time=past_start,
            end_time=past_start + timedelta(minutes=30),
            status=AppointmentStatus.COMPLETED,
        )
        db.add(appt)
        db.flush()
        db.add(Symptom(appointment_id=appt.id, symptom_text="Mild seasonal allergy symptoms, sneezing and itchy eyes."))
        db.add(ClinicalNote(appointment_id=appt.id, doctor_id=doctors[0].id, notes="Diagnosed seasonal allergic rhinitis. Prescribed antihistamine."))
        db.add(Prescription(
            appointment_id=appt.id,
            medicine_name="Cetirizine",
            dosage="10mg",
            frequency="ONCE_DAILY",
            duration="14 days",
            instructions="Take in the evening.",
        ))
        db.commit()

    print("Seed complete.")
    print(f"Admin login: admin@example.com / AdminPass123!")
    print(f"Doctor login: meera.rao@example.com / DoctorPass123!")
    print(f"Patient login: jordan.blake@example.com / PatientPass123!")
    db.close()


if __name__ == "__main__":
    seed()

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import (
    AppointmentStatus,
    HoldStatus,
    TimestampMixin,
    gen_uuid,
)

# Only these statuses count as an "active" booking that occupies a slot.
_ACTIVE_STATUS_SQL = "status IN ('SCHEDULED', 'RESCHEDULED')"


class Appointment(Base, TimestampMixin):
    __tablename__ = "appointments"
    __table_args__ = (
        # Partial unique index: only one ACTIVE (SCHEDULED/RESCHEDULED) appointment
        # can exist for a given doctor+start_time. This is the last line of defense
        # against double-booking even if application-level locking is bypassed.
        Index(
            "uq_active_doctor_slot",
            "doctor_id",
            "start_time",
            unique=True,
            sqlite_where=text(_ACTIVE_STATUS_SQL),
            postgresql_where=text(_ACTIVE_STATUS_SQL),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True, nullable=False)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctors.id"), index=True, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, index=True, nullable=False
    )
    booking_reference: Mapped[str] = mapped_column(String(36), unique=True, default=gen_uuid, nullable=False)

    symptoms: Mapped["Symptom"] = relationship(back_populates="appointment", uselist=False)
    pre_visit_summary: Mapped["PreVisitAISummary"] = relationship(back_populates="appointment", uselist=False)
    clinical_notes: Mapped["ClinicalNote"] = relationship(back_populates="appointment", uselist=False)
    prescriptions: Mapped[list["Prescription"]] = relationship(back_populates="appointment")
    post_visit_summary: Mapped["PostVisitAISummary"] = relationship(back_populates="appointment", uselist=False)


class SlotHold(Base, TimestampMixin):
    """Temporary reservation of a slot while a patient fills the symptom form.

    Holds are advisory/UX-layer: they reduce contention and give the patient
    a window to complete booking, but final booking ALWAYS re-validates
    against the appointments table inside a DB transaction. A hold winning
    does not guarantee the booking will succeed (e.g. it may have expired).
    """

    __tablename__ = "slot_holds"
    __table_args__ = (
        Index("ix_slot_holds_doctor_start", "doctor_id", "start_time"),
        Index("ix_slot_holds_expires_status", "expires_at", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctors.id"), nullable=False)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[HoldStatus] = mapped_column(Enum(HoldStatus), default=HoldStatus.HELD, index=True, nullable=False)
    held_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class Symptom(Base, TimestampMixin):
    __tablename__ = "symptoms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    appointment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("appointments.id"), unique=True, nullable=False
    )
    symptom_text: Mapped[str] = mapped_column(Text, nullable=False)

    appointment: Mapped["Appointment"] = relationship(back_populates="symptoms")


class PreVisitAISummary(Base, TimestampMixin):
    __tablename__ = "pre_visit_ai_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    appointment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("appointments.id"), unique=True, nullable=False
    )
    urgency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_questions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded list
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    appointment: Mapped["Appointment"] = relationship(back_populates="pre_visit_summary")


class ClinicalNote(Base, TimestampMixin):
    __tablename__ = "clinical_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    appointment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("appointments.id"), unique=True, nullable=False
    )
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctors.id"), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)

    appointment: Mapped["Appointment"] = relationship(back_populates="clinical_notes")


class Prescription(Base, TimestampMixin):
    __tablename__ = "prescriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    appointment_id: Mapped[str] = mapped_column(String(36), ForeignKey("appointments.id"), index=True, nullable=False)
    medicine_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str] = mapped_column(String(128), nullable=False)
    frequency: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. ONCE_DAILY, TWICE_DAILY, EVERY_X_HOURS
    duration: Mapped[str | None] = mapped_column(String(64), nullable=True)  # e.g. "7 days"
    instructions: Mapped[str | None] = mapped_column(String(500), nullable=True)

    appointment: Mapped["Appointment"] = relationship(back_populates="prescriptions")


class PostVisitAISummary(Base, TimestampMixin):
    __tablename__ = "post_visit_ai_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    appointment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("appointments.id"), unique=True, nullable=False
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    medication_schedule: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded
    follow_up_steps: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", nullable=False)

    appointment: Mapped["Appointment"] = relationship(back_populates="post_visit_summary")

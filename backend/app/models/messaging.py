from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import (
    CalendarEventStatus,
    CalendarProvider,
    NotificationStatus,
    NotificationType,
    TimestampMixin,
    gen_uuid,
)


class MedicationReminder(Base, TimestampMixin):
    __tablename__ = "medication_reminders"
    __table_args__ = (Index("ix_med_reminder_status_scheduled", "status", "scheduled_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    prescription_id: Mapped[str] = mapped_column(String(36), ForeignKey("prescriptions.id"), nullable=False)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_status_scheduled", "status", "scheduled_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    appointment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("appointments.id"), nullable=True)
    notification_type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)  # email address at send time
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), default=NotificationStatus.PENDING, index=True, nullable=False
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CalendarEvent(Base, TimestampMixin):
    __tablename__ = "calendar_events"
    __table_args__ = (Index("ix_calendar_events_appt_user", "appointment_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    appointment_id: Mapped[str] = mapped_column(String(36), ForeignKey("appointments.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # PATIENT | DOCTOR
    provider: Mapped[CalendarProvider] = mapped_column(Enum(CalendarProvider), default=CalendarProvider.GOOGLE)
    external_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[CalendarEventStatus] = mapped_column(
        Enum(CalendarEventStatus), default=CalendarEventStatus.PENDING, index=True, nullable=False
    )
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)


class GoogleOAuthToken(Base, TimestampMixin):
    """Stores per-user Google OAuth tokens for calendar sync."""

    __tablename__ = "google_oauth_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChatSession(Base, TimestampMixin):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session")


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_session", "session_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user | assistant | tool
    message: Mapped[str] = mapped_column(Text, nullable=False)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class PatientHistoryDocument(Base, TimestampMixin):
    """Metadata row mirroring what's indexed into ChromaDB, kept in Postgres
    so we always have a durable, queryable record of what was embedded."""

    __tablename__ = "patient_history_documents"
    __table_args__ = (Index("ix_history_doc_patient", "patient_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False)
    appointment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("appointments.id"), nullable=True)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)  # symptom|clinical_note|prescription|summary
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    doc_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON-encoded

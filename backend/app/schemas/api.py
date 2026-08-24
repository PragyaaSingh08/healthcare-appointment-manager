from datetime import date, datetime, time

from pydantic import BaseModel, EmailStr, Field


# ---- Auth ----
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class CurrentUserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_email_verified: bool


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class VerifyEmailRequest(BaseModel):
    token: str


# ---- Doctors ----
class WorkingHoursIn(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time


class CreateDoctorRequest(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    specialization: str
    qualification: str | None = None
    experience: int | None = None
    slot_duration: int = 30
    working_hours: list[WorkingHoursIn] = Field(default_factory=list)


class UpdateDoctorRequest(BaseModel):
    specialization: str | None = None
    qualification: str | None = None
    experience: int | None = None
    slot_duration: int | None = None
    is_active: bool | None = None


class DoctorResponse(BaseModel):
    id: str
    name: str
    specialization: str
    qualification: str | None
    experience: int | None
    slot_duration: int
    is_active: bool

    model_config = {"from_attributes": True}


class LeaveRequest(BaseModel):
    leave_date: date
    reason: str | None = None


# ---- Slots / Holds ----
class HoldSlotRequest(BaseModel):
    doctor_id: str
    start_time: datetime


class HoldResponse(BaseModel):
    id: str
    doctor_id: str
    start_time: datetime
    end_time: datetime
    status: str
    expires_at: datetime


class ConfirmHoldRequest(BaseModel):
    symptoms: str = Field(min_length=1)


# ---- Appointments ----
class AppointmentResponse(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    start_time: datetime
    end_time: datetime
    status: str
    booking_reference: str

    model_config = {"from_attributes": True}


class RescheduleRequest(BaseModel):
    hold_id: str  # patient must hold the new slot first, then reschedule against it


# ---- Symptoms / AI ----
class PreVisitSummaryResponse(BaseModel):
    urgency: str | None
    chief_complaint: str | None
    suggested_questions: list[str] | None
    status: str


class ClinicalNoteRequest(BaseModel):
    notes: str = Field(min_length=1)


class PrescriptionItem(BaseModel):
    medicine_name: str
    dosage: str
    frequency: str
    duration: str | None = None
    instructions: str | None = None


class PrescriptionRequest(BaseModel):
    items: list[PrescriptionItem]


class PostVisitSummaryResponse(BaseModel):
    summary: str | None
    medication_schedule: list[dict] | None
    follow_up_steps: list[str] | None
    status: str


# ---- Chat ----
class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1)


class ChatMessageResponse(BaseModel):
    session_id: str
    reply: str

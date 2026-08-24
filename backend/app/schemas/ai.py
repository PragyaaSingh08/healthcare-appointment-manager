from pydantic import BaseModel, Field, field_validator


class PreVisitAIResult(BaseModel):
    urgency: str
    chief_complaint: str
    suggested_questions: list[str] = Field(min_length=1, max_length=5)

    @field_validator("urgency")
    @classmethod
    def urgency_must_be_valid(cls, v: str) -> str:
        allowed = {"Low", "Medium", "High"}
        if v not in allowed:
            raise ValueError(f"urgency must be one of {allowed}, got {v!r}")
        return v


class MedicationScheduleItem(BaseModel):
    medicine: str
    dosage: str
    frequency: str
    instructions: str = ""


class PostVisitAIResult(BaseModel):
    summary: str
    medication_schedule: list[MedicationScheduleItem] = Field(default_factory=list)
    follow_up_steps: list[str] = Field(default_factory=list)

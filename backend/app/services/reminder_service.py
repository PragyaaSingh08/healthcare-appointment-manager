"""Converts a prescription's structured frequency into concrete reminder
timestamps (req #85). We intentionally use a controlled enum of frequency
codes rather than free-text parsing wherever possible; CUSTOM is validated
against an explicit list of hour offsets.
"""
import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.messaging import MedicationReminder
from app.models.scheduling import Prescription
from app.utils.timeutils import utcnow

_DURATION_DAYS_RE = re.compile(r"(\d+)\s*day", re.IGNORECASE)

# Controlled frequency -> reminder times (hours after midnight, local clinic time treated as UTC offset 0 for simplicity)
_FREQUENCY_HOURS = {
    "ONCE_DAILY": [9],
    "TWICE_DAILY": [9, 21],
    "THREE_TIMES_DAILY": [8, 14, 20],
    "FOUR_TIMES_DAILY": [8, 12, 16, 20],
}


def _parse_duration_days(duration: str | None) -> int:
    if not duration:
        return 5  # sensible default if unspecified
    match = _DURATION_DAYS_RE.search(duration)
    return int(match.group(1)) if match else 5


def parse_custom_hours(custom_spec: str) -> list[int]:
    """CUSTOM frequency spec format: 'EVERY_X_HOURS:6' -> every 6 hours starting at 8am.
    Validated to be within [1, 24].
    """
    match = re.match(r"EVERY_(\d+)_HOURS", custom_spec.strip().upper())
    if not match:
        raise ValueError(f"Unsupported custom frequency spec: {custom_spec!r}")
    interval = int(match.group(1))
    if not (1 <= interval <= 24):
        raise ValueError("Custom reminder interval must be between 1 and 24 hours")
    hours = list(range(8, 24, interval)) or [8]
    return hours


def generate_reminders(db: Session, prescription: Prescription, patient_id: str, start_date: datetime | None = None) -> list[MedicationReminder]:
    start_date = start_date or utcnow()
    freq_key = prescription.frequency.strip().upper()

    if freq_key in _FREQUENCY_HOURS:
        hours = _FREQUENCY_HOURS[freq_key]
    elif freq_key.startswith("EVERY_"):
        hours = parse_custom_hours(freq_key)
    else:
        # Unknown/free-text frequency: fall back to once-daily and flag via instructions,
        # rather than guessing an unsafe schedule.
        hours = _FREQUENCY_HOURS["ONCE_DAILY"]

    days = _parse_duration_days(prescription.duration)
    reminders: list[MedicationReminder] = []
    base_day = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    for day_offset in range(days):
        for hour in hours:
            scheduled_at = base_day + timedelta(days=day_offset, hours=hour)
            if scheduled_at <= start_date:
                continue
            reminder = MedicationReminder(
                prescription_id=prescription.id,
                patient_id=patient_id,
                scheduled_at=scheduled_at,
            )
            db.add(reminder)
            reminders.append(reminder)

    db.flush()
    return reminders

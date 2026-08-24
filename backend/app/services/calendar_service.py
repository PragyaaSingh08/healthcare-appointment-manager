"""CalendarService wraps the Google Calendar API. Failures here must never
roll back or block appointment confirmation (req #52) — callers catch
CalendarTransientError/CalendarPermanentError and mark the CalendarEvent row
SYNC_PENDING / FAILED for the worker to retry.
"""
import logging
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import get_settings
from app.models.messaging import GoogleOAuthToken

logger = logging.getLogger("calendar_service")
settings = get_settings()


class CalendarTransientError(Exception):
    pass


class CalendarPermanentError(Exception):
    pass


def _build_credentials(token: GoogleOAuthToken) -> Credentials:
    creds = Credentials(
        token=token.access_token,
        refresh_token=token.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token.access_token = creds.token
    return creds


def create_event(token: GoogleOAuthToken, title: str, description: str, start: datetime, end: datetime) -> str:
    """Returns the external_event_id on success."""
    try:
        creds = _build_credentials(token)
        service = build("calendar", "v3", credentials=creds)
        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start.isoformat()},
            "end": {"dateTime": end.isoformat()},
        }
        created = service.events().insert(calendarId="primary", body=event).execute()
        return created["id"]
    except HttpError as e:
        if e.resp.status in (429, 500, 502, 503, 504):
            raise CalendarTransientError(str(e)) from e
        raise CalendarPermanentError(str(e)) from e
    except Exception as e:
        raise CalendarTransientError(str(e)) from e


def update_event(token: GoogleOAuthToken, external_event_id: str, start: datetime, end: datetime) -> None:
    try:
        creds = _build_credentials(token)
        service = build("calendar", "v3", credentials=creds)
        service.events().patch(
            calendarId="primary",
            eventId=external_event_id,
            body={"start": {"dateTime": start.isoformat()}, "end": {"dateTime": end.isoformat()}},
        ).execute()
    except HttpError as e:
        if e.resp.status in (429, 500, 502, 503, 504):
            raise CalendarTransientError(str(e)) from e
        raise CalendarPermanentError(str(e)) from e
    except Exception as e:
        raise CalendarTransientError(str(e)) from e


def delete_event(token: GoogleOAuthToken, external_event_id: str) -> None:
    try:
        creds = _build_credentials(token)
        service = build("calendar", "v3", credentials=creds)
        service.events().delete(calendarId="primary", eventId=external_event_id).execute()
    except HttpError as e:
        if e.resp.status == 404:
            return  # already gone — treat as success
        if e.resp.status in (429, 500, 502, 503, 504):
            raise CalendarTransientError(str(e)) from e
        raise CalendarPermanentError(str(e)) from e
    except Exception as e:
        raise CalendarTransientError(str(e)) from e

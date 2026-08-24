from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.identity import User
from app.models.messaging import GoogleOAuthToken

router = APIRouter(prefix="/api/calendar", tags=["calendar"])
settings = get_settings()

GOOGLE_AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_SCOPES = "https://www.googleapis.com/auth/calendar.events"


@router.post("/connect")
def connect(user: User = Depends(get_current_user)):
    """Returns the URL the frontend should redirect the user to for Google OAuth consent."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail={"code": "CALENDAR_NOT_CONFIGURED", "message": "Google Calendar integration is not configured."})
    params = (
        f"client_id={settings.GOOGLE_CLIENT_ID}"
        f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&scope={GOOGLE_SCOPES}"
        f"&state={user.id}"
    )
    return {"auth_url": f"{GOOGLE_AUTH_BASE}?{params}"}


@router.get("/callback")
def callback(code: str, state: str, db: Session = Depends(get_db)):
    """Exchanges the authorization code for tokens and stores them for the user
    identified by `state` (the user_id passed through /connect). In production,
    validate `state` as a signed value rather than a raw user_id.
    """
    import httpx

    try:
        resp = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail={"code": "OAUTH_EXCHANGE_FAILED", "message": str(e)})

    data = resp.json()
    user_id = state

    token = db.query(GoogleOAuthToken).filter(GoogleOAuthToken.user_id == user_id).first()
    if not token:
        token = GoogleOAuthToken(user_id=user_id, access_token=data["access_token"], refresh_token=data.get("refresh_token"))
        db.add(token)
    else:
        token.access_token = data["access_token"]
        if data.get("refresh_token"):
            token.refresh_token = data["refresh_token"]
    db.commit()
    return {"status": "connected"}

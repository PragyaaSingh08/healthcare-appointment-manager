import logging
from urllib.parse import quote_plus, urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.identity import User
from app.models.messaging import GoogleOAuthToken

router = APIRouter(prefix="/api/calendar", tags=["calendar"])
logger = logging.getLogger("calendar_oauth")

GOOGLE_AUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_SCOPES = "https://www.googleapis.com/auth/calendar.events"


@router.get("/debug")
def debug_calendar(settings: Settings = Depends(get_settings)):
    """Diagnostic endpoint to inspect Google OAuth configuration."""
    client_id_loaded = bool(settings.GOOGLE_CLIENT_ID and len(settings.GOOGLE_CLIENT_ID.strip()) > 0)
    client_secret_loaded = bool(settings.GOOGLE_CLIENT_SECRET and len(settings.GOOGLE_CLIENT_SECRET.strip()) > 0)
    return {
        "client_id_loaded": client_id_loaded,
        "client_secret_loaded": client_secret_loaded,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "oauth_config_valid": client_id_loaded and client_secret_loaded and bool(settings.GOOGLE_REDIRECT_URI),
    }


@router.post("/connect")
def connect(user: User = Depends(get_current_user), settings: Settings = Depends(get_settings)):
    """Returns the URL the frontend should redirect the user to for Google OAuth consent."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        logger.error("Google Calendar OAuth attempted but credentials are missing in settings.")
        raise HTTPException(
            status_code=503,
            detail={
                "code": "CALENDAR_NOT_CONFIGURED",
                "message": "Google Calendar integration is not configured. Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in backend .env.",
            },
        )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "scope": GOOGLE_SCOPES,
        "state": user.id,
    }
    encoded_params = urlencode(params)
    auth_url = f"{GOOGLE_AUTH_BASE}?{encoded_params}"
    logger.info(
        "Generated Google OAuth URL for user %s. Client ID: %s... Redirect URI: %s",
        user.id,
        settings.GOOGLE_CLIENT_ID[:12] if settings.GOOGLE_CLIENT_ID else "none",
        settings.GOOGLE_REDIRECT_URI,
    )
    return {"auth_url": auth_url}


@router.get("/callback")
def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Exchanges the authorization code for tokens and stores them for the user
    identified by `state` (the user_id passed through /connect).
    """
    logger.info("OAuth callback received: code_present=%s, state=%s, error=%s", bool(code), state, error)

    # Determine if this request is a direct browser navigation from Google OAuth
    accept_header = request.headers.get("accept", "")
    is_direct_browser = "text/html" in accept_header and "application/json" not in accept_header

    if error:
        err_msg = error_description or error
        logger.warning("Google OAuth denied or error received: %s", err_msg)
        if is_direct_browser:
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/calendar/callback?status=error&message={quote_plus(err_msg)}"
            )
        raise HTTPException(
            status_code=400,
            detail={"code": "OAUTH_ACCESS_DENIED", "message": f"Google authorization failed: {err_msg}"},
        )

    if not code or not state:
        logger.error("OAuth callback missing required parameters: code=%s, state=%s", bool(code), state)
        if is_direct_browser:
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/calendar/callback?status=error&message=Missing+authorization+code+or+state"
            )
        raise HTTPException(
            status_code=400,
            detail={"code": "MISSING_PARAMETERS", "message": "Missing authorization code or state parameter."},
        )

    user_id = state
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error("OAuth callback received for non-existent user_id: %s", user_id)
        if is_direct_browser:
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/calendar/callback?status=error&message=User+session+not+found"
            )
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_STATE", "message": "User session not found for this authorization."},
        )

    try:
        logger.info(
            "Exchanging authorization code with Google Token API using redirect_uri: %s",
            settings.GOOGLE_REDIRECT_URI,
        )
        resp = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )
        if resp.is_error:
            logger.error("Google token exchange failed: HTTP %s - %s", resp.status_code, resp.text)
            err_json = {}
            try:
                err_json = resp.json()
            except Exception:
                pass
            err_desc = err_json.get("error_description") or err_json.get("error") or resp.text
            if is_direct_browser:
                return RedirectResponse(
                    url=f"{settings.FRONTEND_URL}/calendar/callback?status=error&message={quote_plus(str(err_desc))}"
                )
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "OAUTH_EXCHANGE_FAILED",
                    "message": f"Google token exchange failed: {err_desc}",
                    "google_error": err_json,
                },
            )
    except httpx.RequestError as e:
        logger.error("Network error connecting to Google token endpoint: %s", str(e))
        if is_direct_browser:
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/calendar/callback?status=error&message=Network+error+connecting+to+Google"
            )
        raise HTTPException(
            status_code=502,
            detail={"code": "OAUTH_EXCHANGE_FAILED", "message": f"Network error during Google token exchange: {str(e)}"},
        )

    data = resp.json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    if not access_token:
        logger.error("Google token response did not contain access_token: %s", data)
        if is_direct_browser:
            return RedirectResponse(
                url=f"{settings.FRONTEND_URL}/calendar/callback?status=error&message=No+access+token+returned+by+Google"
            )
        raise HTTPException(
            status_code=502,
            detail={"code": "OAUTH_EXCHANGE_FAILED", "message": "No access token returned by Google."},
        )

    token = db.query(GoogleOAuthToken).filter(GoogleOAuthToken.user_id == user_id).first()
    if not token:
        token = GoogleOAuthToken(user_id=user_id, access_token=access_token, refresh_token=refresh_token)
        db.add(token)
        logger.info("Persisted new GoogleOAuthToken for user %s", user_id)
    else:
        token.access_token = access_token
        if refresh_token:
            token.refresh_token = refresh_token
        logger.info("Updated existing GoogleOAuthToken for user %s", user_id)
    db.commit()

    if is_direct_browser:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/calendar/callback?status=success")

    return {"status": "connected"}


@router.get("/status")
def calendar_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns whether the current user has connected Google Calendar."""
    token = db.query(GoogleOAuthToken).filter(GoogleOAuthToken.user_id == user.id).first()
    return {"connected": token is not None}

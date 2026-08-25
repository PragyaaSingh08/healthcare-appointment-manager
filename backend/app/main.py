import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import api_router
from app.core.config import get_settings

settings = get_settings()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s")


class _RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


logging.getLogger().addFilter(_RequestIdFilter())

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    logging.getLogger("access").info(
        "%s %s -> %s (%.1fms)", request.method, request.url.path, response.status_code, duration_ms,
        extra={"request_id": request_id},
    )
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        body = {"error": detail}
    else:
        body = {"error": {"code": "ERROR", "message": str(detail)}}
    return JSONResponse(status_code=exc.status_code, content=body)


app.include_router(api_router)


@app.on_event("startup")
def bootstrap_default_admin():
    """Ensures at least one default Admin account exists on application start."""
    from app.core.db import SessionLocal
    from app.core.security import hash_password
    from app.models.base import UserRole
    from app.models.identity import User

    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not admin_exists:
            admin_user = User(
                name="Clinic Admin",
                email="admin@example.com",
                password_hash=hash_password("AdminPass123!"),
                role=UserRole.ADMIN,
                is_active=True,
                is_email_verified=True,
            )
            db.add(admin_user)
            db.commit()
            logging.getLogger("startup").info("Default admin account created")
    except Exception as e:
        db.rollback()
        logging.getLogger("startup").error("Error checking or creating default admin: %s", e)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}

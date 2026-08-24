from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
import hashlib
import secrets

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None


def generate_raw_token() -> str:
    """Cryptographically random, URL-safe token for one-time-use links
    (password reset, email verification). ~256 bits of entropy — not
    guessable, and never itself stored in the DB (see hash_token)."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """One-way hash of a one-time token for DB storage. Using SHA-256 (not
    bcrypt) is intentional here: these tokens are already high-entropy random
    values, not low-entropy user-chosen passwords, so a fast hash is fine and
    avoids unnecessary bcrypt cost on every link click."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "Healthcare Appointment & Follow-up Manager"
    ENV: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./dev.db"

    # Auth
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Groq / AI
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    GROQ_TIMEOUT: int = 20
    GROQ_MAX_RETRIES: int = 3
    GROQ_TEMPERATURE: float = 0.2

    # RAG
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    VECTOR_DB_PATH: str = "./chroma_data"
    RAG_TOP_K: int = 5

    # Email
    EMAIL_PROVIDER: str = "console"  # console | sendgrid | mailgun | smtp
    EMAIL_API_KEY: str = ""
    EMAIL_FROM: str = "no-reply@clinic.example.com"

    # Google Calendar
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/calendar/callback"

    # Slot hold
    SLOT_HOLD_DURATION_SECONDS: int = 300

    # Notification retry
    NOTIFICATION_MAX_ATTEMPTS: int = 5

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # Frontend base URL, used to build links embedded in emails (password
    # reset, email verification).
    FRONTEND_URL: str = "http://localhost:5173"
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 60 * 24


@lru_cache
def get_settings() -> Settings:
    return Settings()

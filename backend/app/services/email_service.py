"""EmailService abstraction. Swappable provider via EMAIL_PROVIDER env var.
Real send failures (timeouts, 5xx, rate limits) raise EmailTransientError so
the worker can distinguish "retry me" from "permanent failure".
"""
from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings

settings = get_settings()


class EmailTransientError(Exception):
    """Raised for retryable failures (timeout, 429, 5xx)."""


class EmailPermanentError(Exception):
    """Raised for non-retryable failures (invalid address, auth failure)."""


class EmailProvider(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None:
        ...


class ConsoleEmailProvider(EmailProvider):
    """Default provider for local/dev — prints instead of sending. Useful when
    no real EMAIL_API_KEY is configured yet."""

    def send(self, to: str, subject: str, body: str) -> None:
        print(f"[EMAIL] to={to} subject={subject!r}\n{body}\n")


class SendGridProvider(EmailProvider):
    def send(self, to: str, subject: str, body: str) -> None:
        if not settings.EMAIL_API_KEY:
            raise EmailPermanentError("SendGrid API key not configured")
        try:
            resp = httpx.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {settings.EMAIL_API_KEY}"},
                json={
                    "personalizations": [{"to": [{"email": to}]}],
                    "from": {"email": settings.EMAIL_FROM},
                    "subject": subject,
                    "content": [{"type": "text/plain", "value": body}],
                },
                timeout=10,
            )
        except httpx.TimeoutException as e:
            raise EmailTransientError(str(e))
        if resp.status_code == 429 or resp.status_code >= 500:
            raise EmailTransientError(f"SendGrid transient error: {resp.status_code}")
        if resp.status_code >= 400:
            raise EmailPermanentError(f"SendGrid rejected request: {resp.status_code} {resp.text}")


class MailgunProvider(EmailProvider):
    def send(self, to: str, subject: str, body: str) -> None:
        if not settings.EMAIL_API_KEY:
            raise EmailPermanentError("Mailgun API key not configured")
        # Domain is expected to be embedded in EMAIL_FROM or a separate setting in production.
        raise NotImplementedError("Configure MAILGUN_DOMAIN and implement per your Mailgun account setup.")


_PROVIDERS = {
    "console": ConsoleEmailProvider,
    "sendgrid": SendGridProvider,
    "mailgun": MailgunProvider,
}


def get_email_provider() -> EmailProvider:
    provider_cls = _PROVIDERS.get(settings.EMAIL_PROVIDER, ConsoleEmailProvider)
    return provider_cls()

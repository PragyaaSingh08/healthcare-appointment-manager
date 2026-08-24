"""GroqService — the ONLY module in the codebase that calls the Groq API.

All other code goes through AIService, which goes through this. This keeps
the model name, retry policy, and timeout configuration in one place (req
#25/#26): changing GROQ_MODEL in .env is sufficient to switch models.
"""
import json
import logging

from groq import Groq
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings

logger = logging.getLogger("groq_service")
settings = get_settings()


class GroqTransientError(Exception):
    pass


class GroqPermanentError(Exception):
    pass


class GroqInvalidJSONError(Exception):
    pass


class GroqService:
    def __init__(self):
        self._client: Groq | None = None

    @property
    def client(self) -> Groq:
        if self._client is None:
            if not settings.GROQ_API_KEY:
                raise GroqPermanentError("GROQ_API_KEY is not configured")
            self._client = Groq(api_key=settings.GROQ_API_KEY, timeout=settings.GROQ_TIMEOUT)
        return self._client

    @retry(
        stop=stop_after_attempt(settings.GROQ_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(GroqTransientError),
        reraise=True,
    )
    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Calls Groq's chat completions API expecting a strict JSON object
        back, and validates it is parseable JSON. Raises typed exceptions so
        callers (AIService) can decide how to degrade gracefully.
        """
        try:
            response = self.client.chat.completions.create(
                model=settings.GROQ_MODEL,
                temperature=settings.GROQ_TEMPERATURE,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
        except Exception as e:  # groq SDK raises various HTTP/timeout errors
            msg = str(e).lower()
            if "timeout" in msg or "429" in msg or "rate" in msg or "5" in msg[:3]:
                raise GroqTransientError(str(e)) from e
            if "401" in msg or "403" in msg or "auth" in msg:
                raise GroqPermanentError(f"Groq authentication error: {e}") from e
            raise GroqTransientError(str(e)) from e

        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError) as e:
            raise GroqInvalidJSONError(f"Groq returned non-JSON content: {e}") from e


groq_service = GroqService()

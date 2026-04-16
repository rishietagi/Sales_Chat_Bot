import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 1.5  # seconds


class GroqInterface:
    """Groq REST API wrapper with exponential-backoff retry logic."""

    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self._call_count = 0

    def generate_explanation(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "llama-3.3-70b-versatile",
    ) -> str:
        """Sends context to Groq and returns the LLM explanation.
        Retries up to 3 times with exponential back-off on transient errors."""

        if not self.api_key or self.api_key == "your_api_key_here":
            return (
                "⚠️ **GROQ_API_KEY NOT CONFIGURED**\n\n"
                "Please add your Groq API key to the `.env` file and restart."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 1024,
        }

        last_error = ""
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                self._call_count += 1
                resp = requests.post(
                    self.url, headers=headers, json=payload, timeout=30
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]

            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else 0
                last_error = str(e)
                # Don't retry on client errors (except 429)
                if 400 <= status < 500 and status != 429:
                    logger.error("Groq API client error (no retry): %s", e)
                    break
                logger.warning(
                    "Groq API error (attempt %d/%d): %s", attempt, _MAX_RETRIES, e
                )
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                logger.warning(
                    "Groq network error (attempt %d/%d): %s", attempt, _MAX_RETRIES, e
                )

            if attempt < _MAX_RETRIES:
                wait = _BACKOFF_BASE ** attempt
                time.sleep(wait)

        return f"**Error connecting to Groq API after {_MAX_RETRIES} attempts:** `{last_error}`"

    @property
    def call_count(self) -> int:
        """Number of API calls made in this session."""
        return self._call_count

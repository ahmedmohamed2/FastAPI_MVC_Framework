import logging
from typing import Any, Dict, Optional

import httpx

from config.settings import settings
from utils.ai_upstream_error import upstream_error_message

logger = logging.getLogger(__name__)


def _openai_uses_max_completion_tokens(model: str) -> bool:
    m = (model or "").lower()
    return (
        m.startswith("gpt-5")
        or "gpt-5" in m
        or m.startswith("o1")
        or m.startswith("o3")
        or m.startswith("o4")
    )


def _openai_omit_temperature(model: str) -> bool:
    """Models that only allow the API default temperature (omit the ``temperature`` field)."""
    m = (model or "").lower()
    return (
        m.startswith("gpt-5")
        or "gpt-5" in m
        or m.startswith("o1")
        or m.startswith("o3")
        or m.startswith("o4")
    )


class OpenAIService:
    """Service for interacting with the OpenAI Chat Completions API."""

    def __init__(self) -> None:
        self.api_key = settings.OPENAI_API_KEY
        self.api_url = settings.OPENAI_API_URL
        self.model = settings.OPENAI_MODEL
        self.client = httpx.AsyncClient(timeout=60.0)
        self.last_error_detail: Optional[str] = None

    def _request_body(self, prompt: str, review_text: str) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": review_text},
            ],
        }
        model = self.model or ""
        if _openai_omit_temperature(model):
            pass
        else:
            body["temperature"] = settings.AI_TEMPERATURE

        if _openai_uses_max_completion_tokens(model):
            body["max_completion_tokens"] = settings.AI_MAX_TOKENS
        else:
            body["max_tokens"] = settings.AI_MAX_TOKENS

        return body

    async def send_request(self, prompt: str, review_text: str) -> Optional[Dict[str, Any]]:
        """
        Send a chat completion request with a system prompt and user message.

        Args:
            prompt: System instructions.
            review_text: User message body (e.g. text to analyze).

        Returns:
            Parsed JSON response from the API, or None if the request failed.
        """
        if not self.model:
            logger.error("OpenAI model is not configured (set OPENAI_MODEL in .env).")
            return None
        if not self.api_key:
            logger.error("OpenAI API key is not configured (set OPENAI_API_KEY in .env).")
            return None

        self.last_error_detail = None
        request_body = self._request_body(prompt, review_text)

        try:
            response = await self.client.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            self.last_error_detail = upstream_error_message(e.response, max_len=4000)
            logger.error(
                "OpenAI API request failed: %s | response: %s",
                e,
                self.last_error_detail,
            )
            return None
        except httpx.HTTPError as e:
            logger.error("OpenAI API request failed: %s", e)
            return None
        except Exception as e:
            logger.error("OpenAI API request failed: %s", e)
            return None

    async def close(self) -> None:
        await self.client.aclose()

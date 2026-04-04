import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx

from config.settings import settings
from utils.ai_upstream_error import upstream_error_message

logger = logging.getLogger(__name__)


def _is_ollama_native_chat_url(url: str) -> bool:
    """True when the URL targets Ollama's native ``POST /api/chat`` (not OpenAI-compatible ``/v1/...``)."""
    path = urlparse(url).path.rstrip("/")
    return path.endswith("/api/chat")


def _normalize_local_response_to_chat_completion(
    raw: Dict[str, Any],
    model: str,
) -> Dict[str, Any]:
    """Map Ollama native (or similar) JSON to an OpenAI-style shape for downstream code."""
    choices = raw.get("choices")
    if isinstance(choices, list) and len(choices) > 0:
        return raw

    msg = raw.get("message")
    if isinstance(msg, dict) and "content" in msg:
        content = msg.get("content")
        text = content if isinstance(content, str) else str(content)
        return {
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "model": raw.get("model", model),
        }
    return raw


class LocalModelService:
    """
    Local chat backends: Ollama native ``/api/chat`` (default) or OpenAI-compatible URLs.
    """

    def __init__(self) -> None:
        self.api_url = settings.LOCAL_MODEL_API_URL
        self.model = settings.LOCAL_MODEL_NAME
        self.api_key = settings.LOCAL_MODEL_API_KEY
        self.client = httpx.AsyncClient(timeout=120.0)
        self.last_error_detail: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request_body(self, prompt: str, review_text: str) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": review_text},
        ]
        if _is_ollama_native_chat_url(self.api_url):
            return {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": settings.AI_TEMPERATURE,
                    "num_predict": settings.AI_MAX_TOKENS,
                },
            }
        return {
            "model": self.model,
            "messages": messages,
            "temperature": settings.AI_TEMPERATURE,
            "max_tokens": settings.AI_MAX_TOKENS,
        }

    async def send_request(self, prompt: str, review_text: str) -> Optional[Dict[str, Any]]:
        """
        Send a chat completion request to the local OpenAI-compatible API.

        Args:
            prompt: System instructions.
            review_text: User message body (e.g. text to analyze).

        Returns:
            Parsed JSON response from the API, or None if the request failed.
        """
        if not self.model:
            logger.error("Local model is not configured (set LOCAL_MODEL_NAME in .env).")
            return None

        self.last_error_detail = None
        request_body = self._request_body(prompt, review_text)

        try:
            response = await self.client.post(
                self.api_url,
                headers=self._headers(),
                json=request_body,
            )
            response.raise_for_status()
            raw = response.json()
            return _normalize_local_response_to_chat_completion(raw, self.model or "")
        except httpx.HTTPStatusError as e:
            self.last_error_detail = upstream_error_message(e.response, max_len=4000)
            logger.error(
                "Local model API request failed: %s | response: %s",
                e,
                self.last_error_detail,
            )
            if self.model and self.last_error_detail and "not found" in self.last_error_detail.lower():
                logger.error(
                    "If using Ollama, pull the model first, e.g.: ollama pull %s",
                    self.model,
                )
            return None
        except httpx.HTTPError as e:
            logger.error("Local model API request failed: %s", e)
            return None
        except Exception as e:
            logger.error("Local model API request failed: %s", e)
            return None

    async def close(self) -> None:
        await self.client.aclose()

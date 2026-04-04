from typing import Any, Dict, Optional, Tuple

from config.settings import settings
from prompts import get_connectivity_test_prompts
from schemas.ai import AIConnectivityResponse
from services import create_ai_chat_service


def _extract_assistant_message(raw: Dict[str, Any]) -> Optional[str]:
    choices = raw.get("choices")
    if not choices or not isinstance(choices, list):
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    msg = first.get("message")
    if not isinstance(msg, dict):
        return None
    content = msg.get("content")
    return content if isinstance(content, str) else None


class AIController:
    """Runs AI calls using the configured provider (OpenAI or local)."""

    async def run_connectivity_test(
        self,
    ) -> Tuple[Optional[AIConnectivityResponse], Optional[str]]:
        """
        Returns ``(response, None)`` on success, or ``(None, upstream_error_message)`` on failure.
        """
        system, user = get_connectivity_test_prompts()
        service = create_ai_chat_service()
        upstream_detail: Optional[str] = None
        try:
            raw = await service.send_request(system, user)
            upstream_detail = getattr(service, "last_error_detail", None)
        finally:
            await service.close()

        if raw is None:
            return None, upstream_detail if isinstance(upstream_detail, str) else None

        return (
            AIConnectivityResponse(
                provider=settings.AI_PROVIDER,
                message=_extract_assistant_message(raw),
                raw=raw,
            ),
            None,
        )

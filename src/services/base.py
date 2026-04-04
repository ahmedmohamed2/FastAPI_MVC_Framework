from typing import Any, Dict, Optional, Protocol


class AIChatService(Protocol):
    """Contract for chat-style AI backends (OpenAI or OpenAI-compatible local servers)."""

    async def send_request(self, prompt: str, review_text: str) -> Optional[Dict[str, Any]]:
        """Send system prompt and user content; return parsed JSON or None on failure."""
        ...

    async def close(self) -> None:
        """Release HTTP resources."""
        ...

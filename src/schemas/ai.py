from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AIConnectivityResponse(BaseModel):
    """Result of the connectivity test against the configured AI provider."""

    provider: str = Field(description="Value of AI_PROVIDER from settings (openai or local).")
    message: Optional[str] = Field(
        None,
        description="Assistant message content when the API returns an OpenAI-style shape.",
    )
    raw: Optional[Dict[str, Any]] = Field(
        None,
        description="Full JSON body from the chat completions API.",
    )

from config.settings import settings

from services.base import AIChatService
from services.local_model_service import LocalModelService
from services.openai_service import OpenAIService


def create_ai_chat_service() -> AIChatService:
    """
    Build the configured AI chat backend.

    ``AI_PROVIDER`` in settings must be ``openai`` or ``local`` (case-insensitive).
    """
    provider = (settings.AI_PROVIDER or "openai").strip().lower()
    if provider == "local":
        return LocalModelService()
    if provider == "openai":
        return OpenAIService()
    raise ValueError(
        f"Unsupported AI_PROVIDER={settings.AI_PROVIDER!r}; use 'openai' or 'local'."
    )

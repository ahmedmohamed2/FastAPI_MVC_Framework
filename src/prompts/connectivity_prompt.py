"""
Shared connectivity test prompts for OpenAI and local (OpenAI-compatible) backends.
"""

from typing import Tuple

SYSTEM_PROMPT = """
You are a connectivity test assistant. The user will send a short test line.
Reply with exactly one plain-text line in this format (no markdown):
TEST_OK <one word summarizing the user message>
""".strip()

USER_PROMPT = """
API ping - confirm you received this and follow the system format.
""".strip()


def get_connectivity_test_prompts() -> Tuple[str, str]:
    """Returns (system_prompt, user_prompt) for ``send_request``."""
    return SYSTEM_PROMPT, USER_PROMPT

from typing import Optional

import httpx


def upstream_error_message(response: Optional[httpx.Response], max_len: int = 2000) -> str:
    """
    Extract a short message from OpenAI-style or Ollama-style error JSON, or fall back to raw body.
    """
    if response is None:
        return ""
    text = (response.text or "")[:max_len]
    try:
        data = response.json()
    except Exception:
        return text
    if not isinstance(data, dict):
        return text
    err = data.get("error")
    if isinstance(err, str):
        return err[:max_len]
    if isinstance(err, dict):
        msg = err.get("message")
        if isinstance(msg, str) and msg.strip():
            return msg[:max_len]
    return text

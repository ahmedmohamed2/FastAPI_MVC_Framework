from datetime import datetime, timedelta
from typing import Any, Optional

from jose import JWTError, jwt

from config.settings import settings


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Build a signed JWT access token with ``exp`` and the caller-supplied claims.

    Copies ``data`` before mutation. Expiry defaults to ``ACCESS_TOKEN_EXPIRE_MINUTES``
    from settings when ``expires_delta`` is omitted.
    """
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT. Returns the claims dict, or ``None`` if invalid/expired.
    """
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        return None

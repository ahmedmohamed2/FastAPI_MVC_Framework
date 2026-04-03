"""
Rate Limiting Middleware using SlowAPI
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from config.settings import settings


def get_rate_limiter() -> Limiter:
    """
    Initialize and return the rate limiter instance.
    Uses IP address as the key function for rate limiting.

    For distributed systems, you can use Redis:
    from slowapi.storage import RedisStorage
    redis_storage = RedisStorage(uri="redis://localhost:6379")
    return Limiter(key_func=get_remote_address, storage=redis_storage)
    """
    return Limiter(
        key_func=get_remote_address,
        default_limits=[settings.RATE_LIMIT_GLOBAL] if settings.RATE_LIMIT_ENABLED else [],
        enabled=settings.RATE_LIMIT_ENABLED,
        headers_enabled=True,
    )


# Create global limiter instance
limiter = get_rate_limiter()


def apply_rate_limit(limit_str: str):
    """If rate limiting is enabled, return SlowAPI limit decorator; otherwise a no-op."""
    if settings.RATE_LIMIT_ENABLED:
        return limiter.limit(limit_str, override_defaults=False)
    return lambda func: func

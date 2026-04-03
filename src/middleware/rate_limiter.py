"""
Rate Limiting Middleware using SlowAPI
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config.settings import settings


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
        default_limits=[settings.RATE_LIMIT_GLOBAL] if settings.RATE_LIMIT_ENABLED else []
    )


# Create global limiter instance
limiter = get_rate_limiter()


def get_rate_limit_exceeded_handler():
    """
    Returns the exception handler for rate limit exceeded errors.
    """
    return _rate_limit_exceeded_handler
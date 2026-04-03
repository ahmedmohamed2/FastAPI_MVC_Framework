"""
Rate Limiting Middleware using SlowAPI
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from config.settings import settings


def get_rate_limiter() -> Limiter:
    """
    Construct the process-wide SlowAPI ``Limiter`` used by route decorators.

    **Keying:** Uses ``get_remote_address`` so each client IP has independent quotas.

    **Default limits:** When ``settings.RATE_LIMIT_ENABLED`` is true, registers
    ``settings.RATE_LIMIT_GLOBAL`` as the default limit list applied in addition to
    per-route limits; when disabled, no default limits are registered and the limiter
    is still constructed with ``enabled=False`` so decorators become inert.

    **Headers:** ``headers_enabled=True`` allows response injection of rate-limit
    metadata where supported.

    **Scaling note:** The default storage is in-memory per process. For multiple
    workers or hosts, swap in shared storage (for example Redis via
    ``slowapi.storage.RedisStorage``) so counts are global.

    Returns:
        Configured ``Limiter`` instance (not a factory).
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
    """
    Return a decorator that applies a SlowAPI limit string, or a no-op when disabled.

    When ``RATE_LIMIT_ENABLED`` is true, returns ``limiter.limit(limit_str,
    override_defaults=False)`` so the route’s limit is **added** to the limiter’s
    default limits rather than replacing them entirely. When false, returns an identity
    lambda ``lambda func: func`` so wrapped route signatures stay unchanged and tests
    can run without a limiter.

    Args:
        limit_str: SlowAPI limit expression (for example ``"200/minute"``).

    Returns:
        A decorator suitable for use with ``@apply_rate_limit(...)`` above FastAPI
        route functions.
    """
    if settings.RATE_LIMIT_ENABLED:
        return limiter.limit(limit_str, override_defaults=False)
    return lambda func: func

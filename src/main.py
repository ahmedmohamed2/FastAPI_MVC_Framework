from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config.settings import settings
from middleware.rate_limiter import limiter
from routers import ai, auth, base, users

app = FastAPI()

app.state.limiter = limiter

if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Global handler for SlowAPI’s ``RateLimitExceeded`` exception.

    When a route decorated with a limit exceeds its quota, SlowAPI raises this
    exception; this handler converts it into an HTTP 429 JSON body that includes a
    short error title, the human-readable detail from the exception, and a stringified
    form of the exception for debugging. If the request has ``view_rate_limit`` state
    attached by SlowAPI, the handler delegates to the limiter’s ``_inject_headers`` so
    standard rate-limit headers (for example ``Retry-After``) are appended to the
    response per library conventions.

    Args:
        request: The request that triggered the limit.
        exc: The SlowAPI exception carrying limit metadata and message.

    Returns:
        A ``JSONResponse`` with status 429 and optional rate-limit headers.
    """
    response = JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": exc.detail,
            "detail": str(exc),
        },
    )
    if hasattr(request.state, "view_rate_limit"):
        response = request.app.state.limiter._inject_headers(
            response, request.state.view_rate_limit
        )
    return response


app.include_router(base.base_router)
app.include_router(auth.auth_router, prefix=settings.API_PREFIX)
app.include_router(users.users_router, prefix=settings.API_PREFIX)
app.include_router(ai.ai_router, prefix=settings.API_PREFIX)

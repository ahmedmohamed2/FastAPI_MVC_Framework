from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config.settings import settings
from middleware.rate_limiter import limiter
from routers import base, users

app = FastAPI()

app.state.limiter = limiter

if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
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
app.include_router(users.users_router, prefix=settings.API_PREFIX)

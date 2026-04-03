from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response
from config.settings import settings
from middleware.rate_limiter import apply_rate_limit

base_router = APIRouter(
    prefix=settings.API_PREFIX,
    tags=["Base"],
)


@base_router.get("/")
@apply_rate_limit(settings.RATE_LIMIT_GET)
async def health_check(request: Request, response: Response):
    """
    Lightweight liveness endpoint mounted at the API prefix root (for example ``/api/v1/``).

    Does not touch the database or external services. Returns a JSON payload with a
    fixed health message plus ``PROJECT_NAME`` and ``APP_VERSION`` from settings so
    clients and load balancers can verify the process is running and identify the
    deployment. Subject to the same GET rate limit configuration as other GET routes
    when rate limiting is enabled.

    Args:
        request: Starlette request (required by the rate-limit wrapper).
        response: Starlette response (required by the rate-limit wrapper).

    Returns:
        ``JSONResponse`` with ``message``, ``project_name``, and ``project_version``.
    """
    project_name    = settings.PROJECT_NAME
    project_version = settings.APP_VERSION
    return JSONResponse(
        content={
            "message": "App is running healty",
            "project_name": project_name,
            "project_version": project_version,
        }
    )

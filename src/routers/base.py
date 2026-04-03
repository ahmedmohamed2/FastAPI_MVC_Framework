from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from config.settings import settings
from middleware.rate_limiter import apply_rate_limit

base_router = APIRouter(
    prefix="/api/v1",
    tags=["Base"]
)


@base_router.get("/")
@apply_rate_limit(settings.RATE_LIMIT_GET)
async def health_check(request: Request):
    project_name    = settings.PROJECT_NAME
    project_version = settings.APP_VERSION
    return JSONResponse(
        content={
            "message": "App is running healty",
            "project_name": project_name,
            "project_version": project_version,
        }
    )

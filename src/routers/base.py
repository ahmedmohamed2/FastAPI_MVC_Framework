from fastapi import FastAPI, APIRouter
from config.settings import settings

base_router = APIRouter(
    prefix="/api/v1",
    tags=["Base"]
)

@base_router.get("/")
async def health_check():
    project_name    = settings.PROJECT_NAME
    project_version = settings.APP_VERSION
    return {
        "message": "App is running healty",
        "project_name": project_name,
        "project_version": project_version
    }

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.responses import Response

from config.settings import settings
from controllers.ai_controller import AIController
from middleware.auth import get_current_user
from middleware.rate_limiter import apply_rate_limit
from models.user import User
from schemas.ai import AIConnectivityResponse

ai_router = APIRouter(prefix="/ai", tags=["AI"])


def get_ai_controller() -> AIController:
    return AIController()


@ai_router.post(
    "/connectivity-test",
    response_model=AIConnectivityResponse,
    status_code=status.HTTP_200_OK,
)
@apply_rate_limit(settings.RATE_LIMIT_POST)
async def connectivity_test(
    request: Request,
    response: Response,
    _current_user: User = Depends(get_current_user),
    controller: AIController = Depends(get_ai_controller),
):
    """
    Run the shared connectivity prompt against the configured AI backend.

    Requires ``Authorization: Bearer <access_token>``. Uses ``AI_PROVIDER`` from
    settings (OpenAI or local OpenAI-compatible API).
    """
    result, upstream_detail = await controller.run_connectivity_test()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=upstream_detail
            or "AI backend request failed or is misconfigured.",
        )
    return result

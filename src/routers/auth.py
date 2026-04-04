from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.responses import Response

from config.settings import settings
from controllers.auth_controller import AuthController
from middleware.auth import (
    get_auth_controller,
    get_current_user,
    get_optional_current_user,
)
from middleware.rate_limiter import apply_rate_limit
from models.user import User
from schemas.auth import LoginRequest, TokenResponse
from schemas.user import UserResponse
from utils.jwt import create_access_token

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


def _profile_name(user: User) -> str | None:
    parts = [p for p in (user.first_name, user.last_name) if p]
    return " ".join(parts) if parts else None


@auth_router.post("/login", response_model=TokenResponse)
@apply_rate_limit(settings.RATE_LIMIT_POST)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    controller: AuthController = Depends(get_auth_controller),
):
    user = controller.authenticate(
        email=str(payload.email),
        password=payload.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token_data: dict = {
        "sub": str(user.id),
        "email": user.email,
    }
    name = _profile_name(user)
    if name:
        token_data["name"] = name
    access_token = create_access_token(token_data)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@auth_router.get("/me", response_model=UserResponse)
@apply_rate_limit(settings.RATE_LIMIT_GET)
async def read_me(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
):
    return current_user


@auth_router.get("/optional-me", response_model=UserResponse | None)
@apply_rate_limit(settings.RATE_LIMIT_GET)
async def read_optional_me(
    request: Request,
    response: Response,
    user: User | None = Depends(get_optional_current_user),
):
    """
    Same as ``/me`` when a valid Bearer token is sent; returns ``null`` when missing
    or invalid (no 401). Demonstrates ``get_optional_current_user``.
    """
    return user

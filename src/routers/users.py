from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.responses import Response

from config.settings import settings
from controllers.user_controller import UserController, UsernameOrEmailExistsError
from database.mysql_session import get_db
from middleware.auth import get_current_user
from enums.user_response_enum import UserResponseEnum
from middleware.rate_limiter import apply_rate_limit
from models.user import User
from schemas.user import (
    UserCreate,
    UserDeleteResponse,
    UserMutationResponse,
    UserResponse,
    UserUpdate,
)

users_router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

_MAX_PAGE_SIZE = 200


def get_user_controller(db: Session = Depends(get_db)) -> UserController:
    """
    FastAPI dependency that wires a request-scoped database session into ``UserController``.

    ``Depends(get_db)`` yields a SQLAlchemy ``Session`` for the lifetime of a single
    request; this factory wraps that session in ``UserController`` so route handlers
    receive a ready-made service object instead of constructing the controller
    manually. The same session is shared with ``get_db``’s teardown, which closes the
    session after the response is sent.

    Args:
        db: Injected ORM session (provided by ``get_db``).

    Returns:
        A ``UserController`` instance bound to ``db``.
    """
    return UserController(db)


@users_router.get(
    "/",
    response_model=list[UserResponse],
)
@apply_rate_limit(settings.RATE_LIMIT_GET)
async def list_users(
    request: Request,
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=_MAX_PAGE_SIZE),
    _current_user: User = Depends(get_current_user),
    controller: UserController = Depends(get_user_controller),
):
    """
    HTTP GET handler for ``GET /users/`` (under the router prefix).

    Requires a valid Bearer JWT. Returns a JSON array of users shaped by
    ``UserResponse``. Pagination uses ``skip`` and ``limit`` (capped at
    ``_MAX_PAGE_SIZE``). Subject to GET rate limits.
    """
    return controller.list_users(skip=skip, limit=limit)


@users_router.get(
    "/me",
    response_model=UserResponse,
)
@apply_rate_limit(settings.RATE_LIMIT_GET)
async def read_current_user_profile(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
):
    """
    Example protected route: returns the authenticated user (Bearer JWT required).
    Declared before ``/{user_id}`` so ``me`` is not parsed as an integer id.
    """
    return current_user


@users_router.get(
    "/{user_id}",
    response_model=UserResponse,
)
@apply_rate_limit(settings.RATE_LIMIT_GET)
async def get_user(
    request: Request,
    response: Response,
    user_id: int,
    _current_user: User = Depends(get_current_user),
    controller: UserController = Depends(get_user_controller),
):
    """
    HTTP GET handler for ``GET /users/{user_id}``.

    Requires a valid Bearer JWT. Loads one user by primary key; 404 if missing.
    """
    user = controller.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=UserResponseEnum.USER_NOT_FOUND.value,
        )
    return user


@users_router.post(
    "/",
    response_model=UserMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
@apply_rate_limit(settings.RATE_LIMIT_POST)
async def create_user(
    request: Request,
    response: Response,
    payload: UserCreate,
    _current_user: User = Depends(get_current_user),
    controller: UserController = Depends(get_user_controller),
):
    """
    HTTP POST handler for ``POST /users/`` creating a new user.

    Requires a valid Bearer JWT. Duplicate username/email returns 409 without insert;
    unique constraint violations (e.g. races) return 409 after rollback.
    """
    try:
        user = controller.create_user(payload)
    except UsernameOrEmailExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=UserResponseEnum.USERNAME_OR_EMAIL_ALREADY_EXISTS.value,
        ) from None
    except IntegrityError:
        controller.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=UserResponseEnum.USERNAME_OR_EMAIL_ALREADY_EXISTS.value,
        ) from None
    return UserMutationResponse(
        message=UserResponseEnum.USER_CREATE_SUCCESS.value,
        user=user,
    )


@users_router.put(
    "/{user_id}",
    response_model=UserMutationResponse,
)
@apply_rate_limit(settings.RATE_LIMIT_PUT)
async def update_user(
    request: Request,
    response: Response,
    user_id: int,
    payload: UserUpdate,
    _current_user: User = Depends(get_current_user),
    controller: UserController = Depends(get_user_controller),
):
    """
    HTTP PUT handler for ``PUT /users/{user_id}`` partial updates.

    Requires a valid Bearer JWT. Empty body yields 400; missing user 404; conflict 409.
    """
    if not payload.model_dump(exclude_unset=True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=UserResponseEnum.NO_FIELDS_TO_UPDATE.value,
        )
    try:
        user = controller.update_user(user_id, payload)
    except IntegrityError:
        controller.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=UserResponseEnum.USERNAME_OR_EMAIL_ALREADY_EXISTS.value,
        ) from None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=UserResponseEnum.USER_NOT_FOUND.value,
        )
    return UserMutationResponse(
        message=UserResponseEnum.USER_UPDATE_SUCCESS.value,
        user=user,
    )


@users_router.delete(
    "/{user_id}",
    response_model=UserDeleteResponse,
)
@apply_rate_limit(settings.RATE_LIMIT_DELETE)
async def delete_user(
    request: Request,
    response: Response,
    user_id: int,
    _current_user: User = Depends(get_current_user),
    controller: UserController = Depends(get_user_controller),
):
    """
    HTTP DELETE handler for ``DELETE /users/{user_id}``.

    Requires a valid Bearer JWT. 404 if the user does not exist.
    """
    deleted = controller.delete_user(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=UserResponseEnum.USER_NOT_FOUND.value,
        )
    return UserDeleteResponse(message=UserResponseEnum.USER_DELETE_SUCCESS.value)

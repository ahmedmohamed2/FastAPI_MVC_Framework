from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.responses import Response

from config.settings import settings
from controllers.user_controller import UserController
from database.mysql_session import get_db
from enums.user_response_enum import UserResponseEnum
from middleware.rate_limiter import apply_rate_limit
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
    controller: UserController = Depends(get_user_controller),
):
    """
    HTTP GET handler for ``GET /users/`` (under the router prefix).

    Returns a JSON array of users shaped by ``UserResponse``. Pagination is driven by
    query parameters: ``skip`` offsets into the full table (non-negative), and ``limit``
    caps the page size (between 1 and ``_MAX_PAGE_SIZE`` inclusive). Rate limiting is
    applied per configured GET quota. The handler delegates all querying to
    ``UserController.list_users`` and does not filter by role or authentication in
    this version of the API.

    Args:
        request: Starlette request (required by the rate-limit decorator for keying).
        response: Starlette response (required by the rate-limit decorator for headers).
        skip: Offset for pagination.
        limit: Page size, upper-bounded for safety.
        controller: Service layer for database access.

    Returns:
        A list of serialized user objects.
    """
    return controller.list_users(skip=skip, limit=limit)


@users_router.get(
    "/{user_id}",
    response_model=UserResponse,
)
@apply_rate_limit(settings.RATE_LIMIT_GET)
async def get_user(
    request: Request,
    response: Response,
    user_id: int,
    controller: UserController = Depends(get_user_controller),
):
    """
    HTTP GET handler for ``GET /users/{user_id}``.

    Loads one user by primary key. If the id does not exist, responds with HTTP 404 and
    a stable message from ``UserResponseEnum.USER_NOT_FOUND``. Successful responses
    use ``UserResponse`` and exclude password material. Subject to GET rate limits.

    Args:
        request: Incoming HTTP request (rate limiter).
        response: Outgoing response object (rate limiter).
        user_id: Path parameter: primary key of the user to fetch.
        controller: User persistence service.

    Returns:
        The requested ``User`` ORM instance, which FastAPI serializes via
        ``response_model``.

    Raises:
        HTTPException: 404 when no row matches ``user_id``.
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
    controller: UserController = Depends(get_user_controller),
):
    """
    HTTP POST handler for ``POST /users/`` creating a new user.

    Accepts a JSON body validated as ``UserCreate``. On success returns HTTP 201 with
    ``UserMutationResponse`` containing a success message and the created user as
    ``UserResponse``. Database unique violations on username or email are translated
    into HTTP 409: the session is rolled back to discard the failed transaction, then
    ``USERNAME_OR_EMAIL_ALREADY_EXISTS`` is returned. Other errors propagate unless
    handled elsewhere. POST rate limits apply.

    Args:
        request: Incoming request (rate limiting).
        response: Response object (rate limiting).
        payload: Validated user creation data.
        controller: Service that performs insert and commit.

    Returns:
        Mutation envelope with message and created user.

    Raises:
        HTTPException: 409 on ``IntegrityError`` after rollback.
    """
    try:
        user = controller.create_user(payload)
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
    controller: UserController = Depends(get_user_controller),
):
    """
    HTTP PUT handler for ``PUT /users/{user_id}`` partial updates.

    Requires at least one field in the JSON body; an empty patch (no keys set) yields
    HTTP 400 with ``NO_FIELDS_TO_UPDATE``. Delegates to ``UserController.update_user``.
    Unique constraint failures produce HTTP 409 after session rollback, same as create.
    If the user id does not exist, returns HTTP 404. Success returns
    ``UserMutationResponse`` with ``USER_UPDATE_SUCCESS``. PUT rate limits apply.

    Args:
        request: Incoming request (rate limiting).
        response: Response object (rate limiting).
        user_id: Path parameter identifying the row to update.
        payload: Partial user fields; omitted keys are left unchanged at the DB layer.
        controller: Service performing load, patch, commit, refresh.

    Returns:
        Mutation envelope with message and updated user.

    Raises:
        HTTPException: 400 for empty body, 404 for missing user, 409 on conflict.
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
    controller: UserController = Depends(get_user_controller),
):
    """
    HTTP DELETE handler for ``DELETE /users/{user_id}``.

    Attempts to delete the user with the given primary key. If ``delete_user`` returns
    ``False`` (no row), responds with 404 and ``USER_NOT_FOUND``. On success returns
    ``UserDeleteResponse`` with ``USER_DELETE_SUCCESS``. DELETE rate limits apply.

    Args:
        request: Incoming request (rate limiting).
        response: Response object (rate limiting).
        user_id: Primary key of the user to delete.
        controller: Service that performs delete and commit.

    Returns:
        A small JSON object containing only a success message.

    Raises:
        HTTPException: 404 when the user does not exist.
    """
    deleted = controller.delete_user(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=UserResponseEnum.USER_NOT_FOUND.value,
        )
    return UserDeleteResponse(message=UserResponseEnum.USER_DELETE_SUCCESS.value)

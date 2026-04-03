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
    deleted = controller.delete_user(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=UserResponseEnum.USER_NOT_FOUND.value,
        )
    return UserDeleteResponse(message=UserResponseEnum.USER_DELETE_SUCCESS.value)

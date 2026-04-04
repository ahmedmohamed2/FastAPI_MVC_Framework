from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from controllers.auth_controller import AuthController
from database.mysql_session import get_db
from models.user import User
from utils.jwt import verify_token

_bearer_optional = HTTPBearer(auto_error=False)


def get_auth_controller(db: Session = Depends(get_db)) -> AuthController:
    return AuthController(db)


def _bearer_unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(_bearer_optional),
    ],
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _bearer_unauthorized()
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise _bearer_unauthorized()
    sub = payload.get("sub")
    if sub is None:
        raise _bearer_unauthorized()
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise _bearer_unauthorized()
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _bearer_unauthorized()
    return user


async def get_optional_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Depends(_bearer_optional),
    ],
    db: Session = Depends(get_db),
) -> Optional[User]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    payload = verify_token(credentials.credentials)
    if payload is None:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user

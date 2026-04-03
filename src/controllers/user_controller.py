from sqlalchemy import select
from sqlalchemy.orm import Session

from models.user import User
from schemas.user import UserCreate, UserUpdate
from utils.password import hash_password


class UserController:
    def __init__(self, db: Session):
        self._db = db

    @property
    def db(self) -> Session:
        return self._db

    def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        stmt = select(User).offset(skip).limit(limit)
        return list(self._db.scalars(stmt).all())

    def get_user_by_id(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def create_user(self, data: UserCreate) -> User:
        user = User(
            username=data.username,
            email=str(data.email),
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            is_active=data.is_active,
        )
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update_user(self, user_id: int, data: UserUpdate) -> User | None:
        user = self._db.get(User, user_id)
        if user is None:
            return None
        payload = data.model_dump(exclude_unset=True)
        if "password" in payload:
            payload["password_hash"] = hash_password(payload.pop("password"))
        if "email" in payload and payload["email"] is not None:
            payload["email"] = str(payload["email"])
        for key, value in payload.items():
            if value is None and key in ("username", "email", "is_active"):
                continue
            setattr(user, key, value)
        self._db.commit()
        self._db.refresh(user)
        return user

    def delete_user(self, user_id: int) -> bool:
        user = self._db.get(User, user_id)
        if user is None:
            return False
        self._db.delete(user)
        self._db.commit()
        return True

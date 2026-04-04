from sqlalchemy import select
from sqlalchemy.orm import Session

from models.user import User
from utils.password import verify_password


class AuthController:
    """Authentication helpers backed by the ``User`` model and bcrypt."""

    def __init__(self, db: Session):
        self._db = db

    @property
    def db(self) -> Session:
        return self._db

    def get_user_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self._db.scalars(stmt).first()

    def authenticate(self, email: str, password: str) -> User | None:
        """
        Return the user if email/password match and the account is active; else ``None``.
        Uses a single generic outcome for all failure cases (unknown user, wrong
        password, inactive account) so callers can map to one error message.
        """
        user = self.get_user_by_email(email)
        if user is None:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

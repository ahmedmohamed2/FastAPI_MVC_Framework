from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from models.user import User
from schemas.user import UserCreate, UserUpdate
from utils.password import hash_password


class UsernameOrEmailExistsError(Exception):
    """Raised when a create would duplicate an existing username or email."""


class UserController:
    """
    Application service layer for user persistence.

    Encapsulates all database operations for the ``User`` ORM model: listing with
    pagination, loading by primary key, creating rows with hashed passwords, applying
    partial updates (including optional password rotation), and hard deletes. Callers
    should use a SQLAlchemy ``Session`` obtained from the request-scoped dependency
    (for example ``get_db``) so that transactions align with the HTTP request lifecycle.
    """

    def __init__(self, db: Session):
        """
        Attach a SQLAlchemy session used for all subsequent user operations on this
        controller instance.

        The session is stored privately so that route handlers can still access it for
        error recovery (for example rolling back after an ``IntegrityError``) via the
        public ``db`` property without breaking encapsulation of the internal attribute
        name.

        Args:
            db: An open ORM session bound to the application engine; must not be closed
                by the caller before the controller finishes its work for the request.
        """
        self._db = db

    @property
    def db(self) -> Session:
        """
        Expose the underlying SQLAlchemy session for callers that need direct access.

        This is primarily used by API routes to call ``rollback()`` when a database
        constraint violation occurs, ensuring the session is left in a clean state
        before raising an HTTP error. Normal read/write paths should prefer the
        controller methods rather than using the session directly.

        Returns:
            The same ``Session`` instance passed to ``__init__``.
        """
        return self._db

    def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """
        Return a window of user rows ordered by the database default for the query.

        Executes a ``SELECT`` on the ``users`` table with ``OFFSET`` and ``LIMIT``
        derived from ``skip`` and ``limit``. No filter is applied: every stored user
        may appear subject to pagination. Does not commit; read-only use of the
        session is sufficient.

        Args:
            skip: Number of rows to skip from the start of the full result set; use for
                pagination (page size ``limit``, page index derived as ``skip // limit``).
            limit: Maximum number of rows to return after ``skip``; must be positive.

        Returns:
            A Python ``list`` of ``User`` ORM instances (possibly empty if ``skip`` is
            beyond the table size). Order matches the database engine’s ordering for an
            unconstrained select (do not rely on a specific order without an explicit
            ``order_by`` in the query).
        """
        stmt = select(User).offset(skip).limit(limit)
        return list(self._db.scalars(stmt).all())

    def get_user_by_id(self, user_id: int) -> User | None:
        """
        Load a single user by primary key using the session identity map.

        Uses SQLAlchemy’s ``Session.get``, which may return a cached instance if the
        same ``user_id`` was already loaded in this session. Does not hit the database
        unnecessarily when the entity is already present.

        Args:
            user_id: Integer primary key of the ``users`` row to retrieve.

        Returns:
            The ``User`` instance if a row with that id exists; ``None`` if no such row
            is found. No exception is raised for a missing id.
        """
        return self._db.get(User, user_id)

    def _user_exists_by_username_or_email(self, username: str, email: str) -> bool:
        stmt = (
            select(User.id)
            .where(or_(User.username == username, User.email == email))
            .limit(1)
        )
        return self._db.scalar(stmt) is not None

    def create_user(self, data: UserCreate) -> User:
        """
        Insert a new user record with a bcrypt-hashed password.

        Maps the validated ``UserCreate`` schema into a new ``User`` ORM object: the
        plaintext ``password`` is never stored; ``hash_password`` produces the
        ``password_hash`` column value. Email is coerced with ``str()`` for consistency
        with the string column type. The new row is added to the session, committed,
        and refreshed so server-generated fields (for example timestamps and id) are
        populated on the returned instance.

        Before inserting, checks whether ``username`` or ``email`` is already taken so
        duplicate requests avoid consuming ``AUTO_INCREMENT`` ids; concurrent creates
        can still race, so unique constraints and ``IntegrityError`` handling remain
        necessary.

        Args:
            data: Incoming create payload already validated by Pydantic (lengths,
                email format, etc.).

        Returns:
            The persisted ``User`` instance after commit and refresh.

        Raises:
            UsernameOrEmailExistsError: If ``username`` or ``email`` already exists.
            sqlalchemy.exc.IntegrityError: If ``username`` or ``email`` violates a
                unique constraint; callers should roll back the session and map this to
                an appropriate HTTP conflict response.
        """
        email_str = str(data.email)
        if self._user_exists_by_username_or_email(data.username, email_str):
            raise UsernameOrEmailExistsError
        user = User(
            username=data.username,
            email=email_str,
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
        """
        Apply a partial update to an existing user and persist changes.

        Loads the user by ``user_id``. Builds an update payload from ``data`` using
        Pydantic’s ``model_dump(exclude_unset=True)`` so only fields present in the
        request body are changed. If a plaintext ``password`` is included, it is
        replaced in the payload by ``password_hash`` via ``hash_password`` and the raw
        password key is removed. Email values are normalized to ``str`` for the ORM.
        For ``username``, ``email``, and ``is_active``, explicit ``None`` values in the
        payload are skipped so those columns are not cleared unintentionally. Commits
        the transaction and refreshes the instance from the database.

        Args:
            user_id: Primary key of the user row to update.
            data: Validated partial user fields from the API layer.

        Returns:
            The refreshed ``User`` after commit, or ``None`` if no user exists for
            ``user_id``.

        Raises:
            sqlalchemy.exc.IntegrityError: If unique constraints (username/email)
                conflict with another row after the update; the session may need
                ``rollback()`` by the caller.
        """
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
        """
        Permanently remove a user row from the database.

        Loads the entity by primary key; if it exists, deletes it in the current session
        and commits. If no row exists, returns ``False`` without issuing a delete.

        Args:
            user_id: Primary key of the user to remove.

        Returns:
            ``True`` if a row was found and deleted; ``False`` if no user had that id.
        """
        user = self._db.get(User, user_id)
        if user is None:
            return False
        self._db.delete(user)
        self._db.commit()
        return True

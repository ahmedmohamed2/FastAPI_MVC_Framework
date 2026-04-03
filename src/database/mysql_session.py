from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields one SQLAlchemy ``Session`` per HTTP request.

    Creates a new session from the module-level ``SessionLocal`` factory, yields it to
    the endpoint or nested dependencies, and **always** closes the session in a
    ``finally`` block after the response is built—whether the request succeeded or
    raised. This pattern prevents connection leaks and keeps transaction boundaries
    aligned with request scope. ``autocommit`` and ``autoflush`` are disabled so the
    application explicitly controls commits (as in ``UserController``).

    Yields:
        An open ``Session`` bound to ``engine``.

    Note:
        Callers must not close the session manually; the generator’s cleanup does.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List, Optional
from urllib.parse import quote_plus
import secrets
import warnings


class Settings(BaseSettings):
    # API Settings
    PROJECT_NAME: str
    APP_VERSION: str
    API_PREFIX: str = "/api/v1"

    # CORS Settings (comma-separated string from .env)
    CORS_ORIGINS: str


    # Rate Limiting Settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_GLOBAL: str = "1000/hour"  # Global limit per IP
    RATE_LIMIT_GET: str = "200/minute"  # GET requests limit
    RATE_LIMIT_POST: str = "50/minute"  # POST requests limit
    RATE_LIMIT_PUT: str = "50/minute"  # PUT requests limit
    RATE_LIMIT_DELETE: str = "50/minute"  # DELETE requests limit

    # JWT Settings
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # OpenAI Settings
    OPENAI_API_KEY: str = ""
    OPENAI_API_URL: str = "https://api.openai.com/v1/chat/completions"
    OPENAI_MODEL: Optional[str] = None  # Must be set explicitly when using OpenAI

    # MySQL / SQLAlchemy
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = ""

    @property
    def database_url(self) -> str:
        """
        Build a SQLAlchemy-compatible MySQL connection URL for PyMySQL.

        URL-encodes username and password with ``quote_plus`` so special characters in
        credentials do not break parsing. The scheme is ``mysql+pymysql`` to select the
        PyMySQL driver with SQLAlchemy. Host, port, and database name are interpolated
        from the corresponding settings fields.

        Returns:
            A single string suitable for ``sqlalchemy.create_engine``.

        Note:
            The password appears in the URL in encoded form; avoid logging this value.
        """
        user = quote_plus(self.MYSQL_USER)
        password = quote_plus(self.MYSQL_PASSWORD)
        return (
            f"mysql+pymysql://{user}:{password}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @model_validator(mode='after')
    def generate_secret_key_if_missing(self):
        """
        Pydantic ``model_validator`` that ensures ``SECRET_KEY`` is non-empty after load.

        If ``SECRET_KEY`` is missing or blank in the environment / ``.env`` file,
        assigns a cryptographically strong random 32-byte URL-safe string from
        ``secrets.token_urlsafe(32)`` and emits a ``UserWarning`` reminding operators
        that production must set an explicit stable secret. This runs once when the
        ``Settings`` instance is constructed, before the module-level ``settings``
        singleton is used by the app.

        Returns:
            ``self`` for validator chaining.

        Warning:
            Auto-generated keys change on every process restart and invalidate tokens;
            set ``SECRET_KEY`` in production.
        """
        if not self.SECRET_KEY:
            self.SECRET_KEY = secrets.token_urlsafe(32)
            warnings.warn(
                "SECRET_KEY not set in .env file. Using auto-generated key for development. "
                "This should be set to a secure random string in production!",
                UserWarning,
                stacklevel=2
            )
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        """
        Parse ``CORS_ORIGINS`` from a comma-separated env string into a list of origins.

        Splits on commas and strips whitespace around each segment so values like
        ``"https://a.com, https://b.com"`` become two clean origin strings. Empty
        segments after strip are still included if present between commas; callers
        configuring CORS middleware should ensure ``CORS_ORIGINS`` is well-formed.

        Returns:
            List of origin strings for use with Starlette/FastAPI CORSMiddleware.
        """
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        """
        Pydantic v1-style inner ``Config`` for ``BaseSettings`` loading behavior.

        Points model construction at the project ``.env`` file with UTF-8 encoding and
        preserves case sensitivity for environment variable names so ``MYSQL_HOST`` and
        similar keys match exactly.
        """

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
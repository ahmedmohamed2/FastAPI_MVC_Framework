from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List, Optional
from pathlib import Path
import secrets
import warnings


class Settings(BaseSettings):
    # API Settings
    PROJECT_NAME: str
    APP_VERSION: str

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


    @model_validator(mode='after')
    def generate_secret_key_if_missing(self):
        """Generate a random secret key if not provided (for development only)"""
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
        """Get CORS origins as a list from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
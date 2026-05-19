"""Application configuration using Pydantic Settings.

Validates all required environment variables at startup.
If any required variable is missing, the application terminates
with a non-zero exit code and a log message indicating which variable is missing.
"""

import logging
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Required variables (no default):
        - DATABASE_URL: PostgreSQL connection string for Neon database
        - JWT_SECRET: Secret key for signing JWT tokens

    Optional variables (with defaults):
        - JWT_ACCESS_TOKEN_EXPIRE_MINUTES: Access token lifetime (default: 15)
        - JWT_REFRESH_TOKEN_EXPIRE_DAYS: Refresh token lifetime (default: 7)
        - DB_POOL_SIZE: Database connection pool size (default: 5)
        - LOW_STOCK_THRESHOLD: Stock level to trigger low-stock alerts (default: 10)
        - RATE_LIMIT_AUTH_PER_MINUTE: Max auth requests per minute per IP (default: 10)
        - MAX_LOGIN_ATTEMPTS: Failed attempts before lockout (default: 5)
        - LOGIN_LOCKOUT_MINUTES: Lockout duration in minutes (default: 15)
    """

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DB_POOL_SIZE: int = 5
    LOW_STOCK_THRESHOLD: int = 10
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    CORS_ORIGINS: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


def get_settings() -> Settings:
    """Load and validate application settings.

    Returns the Settings instance if all required variables are present.
    Terminates the process with exit code 1 if validation fails.
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

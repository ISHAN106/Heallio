"""
Configuration management for the application.
Loads environment variables and provides typed configuration.
"""

import os
from functools import lru_cache
from typing import List

from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET_KEY")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    REFRESH_TOKEN_EXPIRATION_DAYS: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRATION_DAYS", "7")
    )

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/ai_health",
    )

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8081"
        ).split(",")
    ]

    # API
    API_TITLE: str = os.getenv("API_TITLE", "Heallio API")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    ENABLE_SCHEDULER: bool = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
    LOGIN_RATE_LIMIT: int = int(os.getenv("LOGIN_RATE_LIMIT", "10"))
    LOGIN_RATE_WINDOW_SECONDS: int = int(
        os.getenv("LOGIN_RATE_WINDOW_SECONDS", "60")
    )
    CHAT_RATE_LIMIT: int = int(os.getenv("CHAT_RATE_LIMIT", "40"))
    CHAT_RATE_WINDOW_SECONDS: int = int(os.getenv("CHAT_RATE_WINDOW_SECONDS", "60"))
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    CHAT_MAX_TOKENS: int = int(os.getenv("CHAT_MAX_TOKENS", "512"))
    MAX_FAILED_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_SECONDS: int = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "300"))

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"

    def validate(self) -> None:
        """Validate critical configuration settings."""
        if self.SECRET_KEY == "CHANGE_THIS_SECRET_KEY":
            # Only development may run on the placeholder key; any other
            # environment (staging/production/etc.) must set a real secret.
            if not self.is_development:
                raise ValueError(
                    "SECRET_KEY must be changed outside development! Set it in .env file."
                )
            import logging

            logging.getLogger(__name__).warning(
                "Using the default placeholder SECRET_KEY — acceptable for local "
                "development only. Set SECRET_KEY in .env for any shared environment."
            )

        if "*" in self.ALLOWED_ORIGINS and self.is_production:
            raise ValueError(
                "CORS wildcard '*' is not allowed in production! Specify exact origins in .env."
            )


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings (cached).
    Returns the same instance for the entire application lifetime.
    """
    settings = Settings()
    settings.validate()
    return settings

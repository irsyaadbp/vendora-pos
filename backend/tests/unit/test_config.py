"""Unit tests for backend configuration with Pydantic Settings."""

import subprocess
import sys

import pytest

from app.core.config import Settings, get_settings


class TestSettings:
    """Tests for the Settings class."""

    def test_settings_loads_with_all_required_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings loads successfully when all required env vars are set."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET", "test-secret-key-123")

        settings = Settings()  # type: ignore[call-arg]

        assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost/db"
        assert settings.JWT_SECRET == "test-secret-key-123"

    def test_settings_default_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings uses correct default values for optional variables."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET", "test-secret-key-123")

        settings = Settings()  # type: ignore[call-arg]

        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 15
        assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7
        assert settings.DB_POOL_SIZE == 5
        assert settings.LOW_STOCK_THRESHOLD == 10
        assert settings.RATE_LIMIT_AUTH_PER_MINUTE == 10
        assert settings.MAX_LOGIN_ATTEMPTS == 5
        assert settings.LOGIN_LOCKOUT_MINUTES == 15

    def test_settings_overrides_defaults_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings overrides default values when env vars are set."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET", "test-secret-key-123")
        monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        monkeypatch.setenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "14")
        monkeypatch.setenv("DB_POOL_SIZE", "10")
        monkeypatch.setenv("LOW_STOCK_THRESHOLD", "20")
        monkeypatch.setenv("RATE_LIMIT_AUTH_PER_MINUTE", "5")
        monkeypatch.setenv("MAX_LOGIN_ATTEMPTS", "3")
        monkeypatch.setenv("LOGIN_LOCKOUT_MINUTES", "30")

        settings = Settings()  # type: ignore[call-arg]

        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 14
        assert settings.DB_POOL_SIZE == 10
        assert settings.LOW_STOCK_THRESHOLD == 20
        assert settings.RATE_LIMIT_AUTH_PER_MINUTE == 5
        assert settings.MAX_LOGIN_ATTEMPTS == 3
        assert settings.LOGIN_LOCKOUT_MINUTES == 30

    def test_settings_fails_without_database_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings raises ValidationError when DATABASE_URL is missing."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("JWT_SECRET", "test-secret-key-123")

        with pytest.raises(Exception):
            Settings()  # type: ignore[call-arg]

    def test_settings_fails_without_jwt_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings raises ValidationError when JWT_SECRET is missing."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.delenv("JWT_SECRET", raising=False)

        with pytest.raises(Exception):
            Settings()  # type: ignore[call-arg]

    def test_settings_fails_without_any_required_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Settings raises ValidationError when all required vars are missing."""
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)

        with pytest.raises(Exception):
            Settings()  # type: ignore[call-arg]


class TestGetSettings:
    """Tests for the get_settings function."""

    def test_get_settings_returns_settings_when_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_settings returns a Settings instance when env vars are valid."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET", "test-secret-key-123")

        settings = get_settings()

        assert isinstance(settings, Settings)
        assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost/db"

    def test_get_settings_exits_on_missing_vars(self) -> None:
        """get_settings terminates with non-zero exit code when required vars are missing."""
        # Run in a subprocess to test sys.exit behavior without affecting test process
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os; "
                "os.environ.pop('DATABASE_URL', None); "
                "os.environ.pop('JWT_SECRET', None); "
                "from app.core.config import get_settings; "
                "get_settings()",
            ],
            capture_output=True,
            text=True,
            cwd="/Users/irsyaad/Project/vendora-pos/backend",
        )

        assert result.returncode != 0

"""Unit tests for database infrastructure module."""

from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool


class TestDatabaseEngine:
    """Tests for the database engine configuration."""

    def test_engine_uses_async_adapted_queue_pool(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Engine is configured with AsyncAdaptedQueuePool for connection pooling."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET", "test-secret")

        with patch("app.infrastructure.database.get_settings") as mock_settings:
            from app.core.config import Settings

            mock_settings.return_value = Settings()  # type: ignore[call-arg]

            # Re-import to get fresh module with patched settings
            import importlib

            import app.infrastructure.database as db_module

            importlib.reload(db_module)

            assert isinstance(db_module.engine, AsyncEngine)
            assert db_module.engine.pool.__class__.__name__ == "AsyncAdaptedQueuePool"

    def test_engine_pool_size_matches_config(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Engine pool size matches the DB_POOL_SIZE setting."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET", "test-secret")
        monkeypatch.setenv("DB_POOL_SIZE", "7")

        with patch("app.infrastructure.database.get_settings") as mock_settings:
            from app.core.config import Settings

            mock_settings.return_value = Settings()  # type: ignore[call-arg]

            import importlib

            import app.infrastructure.database as db_module

            importlib.reload(db_module)

            assert db_module.engine.pool.size() == 7

    def test_engine_default_pool_size_is_5(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Engine uses default pool size of 5 when not configured."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET", "test-secret")
        monkeypatch.delenv("DB_POOL_SIZE", raising=False)

        with patch("app.infrastructure.database.get_settings") as mock_settings:
            from app.core.config import Settings

            mock_settings.return_value = Settings()  # type: ignore[call-arg]

            import importlib

            import app.infrastructure.database as db_module

            importlib.reload(db_module)

            assert db_module.engine.pool.size() == 5

    def test_engine_url_converts_postgresql_to_asyncpg(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Engine converts postgresql:// URLs to postgresql+asyncpg://."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET", "test-secret")

        with patch("app.infrastructure.database.get_settings") as mock_settings:
            from app.core.config import Settings

            mock_settings.return_value = Settings()  # type: ignore[call-arg]

            import importlib

            import app.infrastructure.database as db_module

            importlib.reload(db_module)

            assert "asyncpg" in str(db_module.engine.url)

    def test_engine_preserves_asyncpg_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Engine preserves URLs that already use postgresql+asyncpg://."""
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db"
        )
        monkeypatch.setenv("JWT_SECRET", "test-secret")

        with patch("app.infrastructure.database.get_settings") as mock_settings:
            from app.core.config import Settings

            mock_settings.return_value = Settings()  # type: ignore[call-arg]

            import importlib

            import app.infrastructure.database as db_module

            importlib.reload(db_module)

            url_str = str(db_module.engine.url)
            assert "asyncpg" in url_str
            # Should not have double asyncpg
            assert "asyncpg+asyncpg" not in url_str


class TestSessionFactory:
    """Tests for the async session factory."""

    def test_session_factory_is_async_sessionmaker(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Session factory is an async_sessionmaker instance."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET", "test-secret")

        with patch("app.infrastructure.database.get_settings") as mock_settings:
            from app.core.config import Settings

            mock_settings.return_value = Settings()  # type: ignore[call-arg]

            import importlib

            import app.infrastructure.database as db_module

            importlib.reload(db_module)

            assert isinstance(db_module.async_session_factory, async_sessionmaker)


class TestGetDbSession:
    """Tests for the get_db_session dependency."""

    @pytest.mark.asyncio
    async def test_get_db_session_yields_async_session(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_db_session yields an AsyncSession instance."""
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
        monkeypatch.setenv("JWT_SECRET", "test-secret")

        with patch("app.infrastructure.database.get_settings") as mock_settings:
            from app.core.config import Settings

            mock_settings.return_value = Settings()  # type: ignore[call-arg]

            import importlib

            import app.infrastructure.database as db_module

            importlib.reload(db_module)

            gen = db_module.get_db_session()
            session = await gen.__anext__()

            assert isinstance(session, AsyncSession)

            # Clean up
            try:
                await gen.__anext__()
            except StopAsyncIteration:
                pass


class TestBase:
    """Tests for the declarative Base class."""

    def test_base_is_declarative_base(self) -> None:
        """Base is a proper SQLAlchemy DeclarativeBase subclass."""
        from sqlalchemy.orm import DeclarativeBase

        from app.models.base import Base

        assert issubclass(Base, DeclarativeBase)

    def test_base_has_metadata(self) -> None:
        """Base has a metadata attribute for table definitions."""
        from app.models.base import Base

        assert Base.metadata is not None

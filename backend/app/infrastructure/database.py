"""Database engine, session factory, and connection management.

Configures an async SQLAlchemy engine with connection pooling for
Neon PostgreSQL, including SSL support for secure connections.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.core.config import get_settings

settings = get_settings()

# Ensure the DATABASE_URL uses the asyncpg driver
_database_url = settings.DATABASE_URL
if _database_url.startswith("postgresql://"):
    _database_url = _database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
# Remove sslmode query param — asyncpg uses ssl=True via connect_args instead
if "?sslmode=" in _database_url:
    _database_url = _database_url.split("?sslmode=")[0]
elif "&sslmode=" in _database_url:
    _database_url = _database_url.replace("&sslmode=require", "")

# Create async engine with connection pooling and SSL for Neon PostgreSQL
engine = create_async_engine(
    _database_url,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_POOL_SIZE * 2,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"ssl": True},
    echo=False,
)

# Session factory for creating async database sessions
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session.

    Yields an AsyncSession and ensures it is closed after use.
    Use this as a FastAPI dependency for request-scoped sessions.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Dispose the engine and close all pooled connections.

    Call this during application shutdown to cleanly release resources.
    """
    await engine.dispose()

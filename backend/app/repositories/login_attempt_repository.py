"""SQLAlchemy implementation of LoginAttemptRepositoryInterface.

Provides async database operations for tracking login attempts,
used for account lockout detection after consecutive failures.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interfaces import LoginAttemptRepositoryInterface
from app.models.login_attempt import LoginAttempt


class LoginAttemptRepository(LoginAttemptRepositoryInterface):
    """Concrete implementation of LoginAttemptRepositoryInterface using SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations.
        """
        self._session = session

    async def create(
        self,
        user_id: uuid.UUID,
        success: bool,
    ) -> LoginAttempt:
        """Record a login attempt."""
        attempt = LoginAttempt(
            user_id=user_id,
            success=success,
        )
        self._session.add(attempt)
        await self._session.flush()
        await self._session.refresh(attempt)
        return attempt

    async def get_recent_failures(
        self,
        user_id: uuid.UUID,
        since: datetime,
    ) -> list[LoginAttempt]:
        """Get recent failed login attempts since a given timestamp.

        Returns failed attempts ordered by most recent first,
        used to determine if account lockout threshold is reached.
        """
        stmt = (
            select(LoginAttempt)
            .where(
                LoginAttempt.user_id == user_id,
                LoginAttempt.success.is_(False),
                LoginAttempt.attempted_at >= since,
            )
            .order_by(LoginAttempt.attempted_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

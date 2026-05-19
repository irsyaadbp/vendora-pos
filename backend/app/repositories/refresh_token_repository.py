"""SQLAlchemy implementation of RefreshTokenRepositoryInterface.

Provides async database operations for refresh token management,
supporting token rotation and family-based invalidation.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.interfaces import RefreshTokenRepositoryInterface
from app.models.refresh_token import RefreshToken


class RefreshTokenRepository(RefreshTokenRepositoryInterface):
    """Concrete implementation of RefreshTokenRepositoryInterface using SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations.
        """
        self._session = session

    async def create(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        token_family: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Store a new refresh token record."""
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            token_family=token_family,
            expires_at=expires_at,
        )
        self._session.add(token)
        await self._session.flush()
        await self._session.refresh(token)
        return token

    async def get_by_token_hash(self, token_hash: str) -> Optional[RefreshToken]:
        """Retrieve a refresh token by its hash."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token_id: uuid.UUID) -> None:
        """Revoke a single refresh token by setting is_revoked to True."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(is_revoked=True)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def revoke_family(self, token_family: str) -> None:
        """Revoke all refresh tokens in a token family."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.token_family == token_family)
            .values(is_revoked=True)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke all refresh tokens for a specific user."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(is_revoked=True)
        )
        await self._session.execute(stmt)
        await self._session.flush()

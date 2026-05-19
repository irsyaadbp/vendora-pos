"""SQLAlchemy implementation of UserRepositoryInterface.

Provides async database operations for user management using
SQLAlchemy's async session.
"""

import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import PaginationParams
from app.domain.interfaces import PaginatedResult, UserFilters, UserRepositoryInterface
from app.models.user import User
from app.schemas.enums import UserRole


class UserRepository(UserRepositoryInterface):
    """Concrete implementation of UserRepositoryInterface using SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations.
        """
        self._session = session

    async def create(
        self,
        full_name: str,
        email: str,
        password_hash: str,
        role: UserRole,
    ) -> User:
        """Create a new user record in the database."""
        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            role=role,
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Retrieve a user by their UUID."""
        stmt = select(User).where(User.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve a user by their email address."""
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self,
        user_id: uuid.UUID,
        **kwargs: object,
    ) -> Optional[User]:
        """Update a user's fields by ID."""
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def list(
        self,
        filters: UserFilters,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """List users with filtering and pagination."""
        stmt = select(User)
        count_stmt = select(func.count()).select_from(User)

        # Apply search filter (name or email)
        if filters.search:
            search_term = f"%{filters.search}%"
            search_condition = or_(
                User.full_name.ilike(search_term),
                User.email.ilike(search_term),
            )
            stmt = stmt.where(search_condition)
            count_stmt = count_stmt.where(search_condition)

        # Apply role filter
        if filters.role is not None:
            stmt = stmt.where(User.role == filters.role)
            count_stmt = count_stmt.where(User.role == filters.role)

        # Apply active status filter
        if filters.is_active is not None:
            stmt = stmt.where(User.is_active == filters.is_active)
            count_stmt = count_stmt.where(User.is_active == filters.is_active)

        # Get total count
        count_result = await self._session.execute(count_stmt)
        total_count = count_result.scalar_one()

        # Apply ordering and pagination
        stmt = stmt.order_by(User.created_at.desc())
        stmt = stmt.offset(pagination.offset).limit(pagination.limit)

        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return PaginatedResult(items=items, total_count=total_count)

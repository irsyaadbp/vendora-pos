"""SQLAlchemy implementation of CategoryRepositoryInterface.

Provides async database operations for category management using
SQLAlchemy's async session.
"""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import PaginationParams
from app.domain.interfaces import CategoryRepositoryInterface, PaginatedResult
from app.models.category import Category


class CategoryRepository(CategoryRepositoryInterface):
    """Concrete implementation of CategoryRepositoryInterface using SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations.
        """
        self._session = session

    async def create(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> Category:
        """Create a new category record in the database."""
        category = Category(
            name=name,
            description=description,
        )
        self._session.add(category)
        await self._session.flush()
        await self._session.refresh(category)
        return category

    async def get_by_id(self, category_id: uuid.UUID) -> Optional[Category]:
        """Retrieve a category by its UUID."""
        stmt = select(Category).where(Category.id == category_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Category]:
        """Retrieve a category by its name."""
        stmt = select(Category).where(Category.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """List categories with pagination."""
        stmt = select(Category)
        count_stmt = select(func.count()).select_from(Category)

        # Get total count
        count_result = await self._session.execute(count_stmt)
        total_count = count_result.scalar_one()

        # Apply ordering and pagination
        stmt = stmt.order_by(Category.name.asc())
        stmt = stmt.offset(pagination.offset).limit(pagination.limit)

        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return PaginatedResult(items=items, total_count=total_count)

    async def update(
        self,
        category_id: uuid.UUID,
        **kwargs: object,
    ) -> Optional[Category]:
        """Update a category's fields by ID."""
        category = await self.get_by_id(category_id)
        if category is None:
            return None

        for key, value in kwargs.items():
            if hasattr(category, key):
                setattr(category, key, value)

        await self._session.flush()
        await self._session.refresh(category)
        return category

    async def delete(self, category_id: uuid.UUID) -> None:
        """Delete a category by its ID."""
        category = await self.get_by_id(category_id)
        if category is not None:
            await self._session.delete(category)
            await self._session.flush()

"""SQLAlchemy implementation of InventoryLogRepositoryInterface.

Provides async database operations for inventory log management using
SQLAlchemy's async session, including paginated listing sorted by
timestamp descending.
"""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import PaginationParams
from app.domain.interfaces import InventoryLogRepositoryInterface, PaginatedResult
from app.models.inventory_log import InventoryLog
from app.schemas.enums import AdjustmentType


class InventoryLogRepository(InventoryLogRepositoryInterface):
    """Concrete implementation of InventoryLogRepositoryInterface using SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations.
        """
        self._session = session

    async def create(
        self,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        adjustment_type: AdjustmentType,
        quantity_change: int,
        reason: Optional[str] = None,
    ) -> InventoryLog:
        """Create a new inventory log entry in the database."""
        log_entry = InventoryLog(
            product_id=product_id,
            user_id=user_id,
            adjustment_type=adjustment_type,
            quantity_change=quantity_change,
            reason=reason,
        )
        self._session.add(log_entry)
        await self._session.flush()
        await self._session.refresh(log_entry)
        return log_entry

    async def list_by_product(
        self,
        product_id: uuid.UUID,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """List inventory logs for a product, sorted by created_at descending."""
        # Count total matching records
        count_stmt = (
            select(func.count())
            .select_from(InventoryLog)
            .where(InventoryLog.product_id == product_id)
        )
        count_result = await self._session.execute(count_stmt)
        total_count = count_result.scalar_one()

        # Fetch paginated results sorted by timestamp desc
        stmt = (
            select(InventoryLog)
            .where(InventoryLog.product_id == product_id)
            .order_by(InventoryLog.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return PaginatedResult(items=items, total_count=total_count)

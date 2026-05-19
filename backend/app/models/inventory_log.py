"""InventoryLog SQLAlchemy model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.schemas.enums import AdjustmentType


class InventoryLog(Base):
    """InventoryLog model tracking stock movements and adjustments."""

    __tablename__ = "inventory_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    adjustment_type: Mapped[AdjustmentType] = mapped_column(
        SQLEnum(AdjustmentType)
    )
    quantity_change: Mapped[int] = mapped_column(Integer)
    reason: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )

    # Relationships
    product: Mapped["Product"] = relationship(  # noqa: F821
        back_populates="inventory_logs", lazy="selectin"
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        back_populates="inventory_logs", lazy="selectin"
    )

"""Transaction and TransactionItem SQLAlchemy models."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.schemas.enums import PaymentMethod, TransactionStatus


class Transaction(Base):
    """Transaction model representing completed sales."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    cashier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00")
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        SQLEnum(PaymentMethod)
    )
    status: Mapped[TransactionStatus] = mapped_column(
        SQLEnum(TransactionStatus)
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )

    # Relationships
    cashier: Mapped["User"] = relationship(  # noqa: F821
        back_populates="transactions", lazy="selectin"
    )
    items: Mapped[list["TransactionItem"]] = relationship(
        back_populates="transaction", lazy="selectin", cascade="all, delete-orphan"
    )


class TransactionItem(Base):
    """TransactionItem model representing individual line items in a transaction."""

    __tablename__ = "transaction_items"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transactions.id", ondelete="CASCADE")
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT")
    )
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        back_populates="items", lazy="selectin"
    )
    product: Mapped["Product"] = relationship(  # noqa: F821
        back_populates="transaction_items", lazy="selectin"
    )

"""SQLAlchemy implementation of TransactionRepositoryInterface.

Provides async database operations for transaction management including
atomic transaction creation with stock validation and decrement,
paginated listing with role-scoped filtering, and filter support.
"""

import uuid
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import PaginationParams
from app.domain.interfaces import PaginatedResult, TransactionFilters, TransactionRepositoryInterface
from app.models.product import Product
from app.models.transaction import Transaction, TransactionItem
from app.schemas.enums import PaymentMethod, TransactionStatus


class TransactionRepository(TransactionRepositoryInterface):
    """Concrete implementation of TransactionRepositoryInterface using SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations.
        """
        self._session = session

    async def create(
        self,
        cashier_id: uuid.UUID,
        total_amount: object,
        discount_amount: object,
        payment_method: PaymentMethod,
        items: list[dict],
    ) -> Transaction:
        """Atomically create a transaction with items and decrement stock.

        Performs all operations within the current session's transaction:
        1. Validates stock availability for all items (with row-level locking)
        2. Inserts the transaction record
        3. Inserts all transaction item records
        4. Decrements product stock for each item

        If any product has insufficient stock, raises ValueError and the
        caller should handle rollback.

        Args:
            cashier_id: UUID of the cashier processing the transaction.
            total_amount: Total transaction amount (Decimal).
            discount_amount: Discount applied (Decimal).
            payment_method: Payment method used.
            items: List of dicts with keys: product_id, quantity, unit_price, subtotal.

        Returns:
            The created Transaction instance with items loaded.

        Raises:
            ValueError: If any product has insufficient stock, with a message
                        containing the product IDs that lack stock.
        """
        # Step 1: Validate stock for all items using FOR UPDATE to lock rows
        product_ids = [item["product_id"] for item in items]
        stmt = (
            select(Product)
            .where(Product.id.in_(product_ids))
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        products = {p.id: p for p in result.scalars().all()}

        # Check stock availability
        insufficient_stock = []
        for item in items:
            product_id = item["product_id"]
            product = products.get(product_id)
            if product is None:
                insufficient_stock.append(str(product_id))
            elif product.stock < item["quantity"]:
                insufficient_stock.append(str(product_id))

        if insufficient_stock:
            raise ValueError(
                f"Insufficient stock for products: {', '.join(insufficient_stock)}"
            )

        # Step 2: Create the transaction record
        transaction = Transaction(
            cashier_id=cashier_id,
            total_amount=total_amount,
            discount_amount=discount_amount,
            payment_method=payment_method,
            status=TransactionStatus.completed,
        )
        self._session.add(transaction)
        await self._session.flush()

        # Step 3: Create transaction item records
        for item in items:
            transaction_item = TransactionItem(
                transaction_id=transaction.id,
                product_id=item["product_id"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                subtotal=item["subtotal"],
            )
            self._session.add(transaction_item)

        # Step 4: Decrement stock for each product
        for item in items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            stmt_update = (
                update(Product)
                .where(Product.id == product_id)
                .values(stock=Product.stock - quantity)
            )
            await self._session.execute(stmt_update)

        await self._session.flush()
        await self._session.refresh(transaction)

        return transaction

    async def get_by_id(self, transaction_id: uuid.UUID) -> Optional[Transaction]:
        """Retrieve a transaction by its UUID with items loaded."""
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        filters: TransactionFilters,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """List transactions with filtering and pagination.

        Supports role-scoped filtering:
        - user_scope restricts to a specific cashier's transactions (staff).
        - cashier_id filters by cashier (admin filter, overridden by user_scope).
        - payment_method filters by payment method.
        - date_from/date_to filter by creation date range.
        """
        stmt = select(Transaction)
        count_stmt = select(func.count()).select_from(Transaction)

        # Apply role-scoped filter (staff sees only own transactions)
        if filters.user_scope is not None:
            stmt = stmt.where(Transaction.cashier_id == filters.user_scope)
            count_stmt = count_stmt.where(Transaction.cashier_id == filters.user_scope)
        elif filters.cashier_id is not None:
            # Admin filtering by specific cashier
            stmt = stmt.where(Transaction.cashier_id == filters.cashier_id)
            count_stmt = count_stmt.where(Transaction.cashier_id == filters.cashier_id)

        # Apply payment method filter
        if filters.payment_method is not None:
            stmt = stmt.where(Transaction.payment_method == filters.payment_method)
            count_stmt = count_stmt.where(Transaction.payment_method == filters.payment_method)

        # Apply date range filters
        if filters.date_from is not None:
            stmt = stmt.where(Transaction.created_at >= filters.date_from)
            count_stmt = count_stmt.where(Transaction.created_at >= filters.date_from)

        if filters.date_to is not None:
            stmt = stmt.where(Transaction.created_at <= filters.date_to)
            count_stmt = count_stmt.where(Transaction.created_at <= filters.date_to)

        # Get total count
        count_result = await self._session.execute(count_stmt)
        total_count = count_result.scalar_one()

        # Apply ordering (most recent first) and pagination
        stmt = stmt.order_by(Transaction.created_at.desc())
        stmt = stmt.offset(pagination.offset).limit(pagination.limit)

        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return PaginatedResult(items=items, total_count=total_count)

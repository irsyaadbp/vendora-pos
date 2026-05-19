"""Transaction processing service.

Provides POS transaction creation with cart validation, discount calculation,
stock verification, and atomic processing. Also provides role-scoped
transaction listing with pagination and filtering.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.core.dependencies import PaginationParams
from app.core.exceptions import NotFoundException, ValidationException
from app.domain.interfaces import (
    PaginatedResult,
    ProductRepositoryInterface,
    TransactionFilters,
    TransactionRepositoryInterface,
)
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.common import FieldError
from app.schemas.enums import DiscountType, PaymentMethod, UserRole


@dataclass
class ReceiptItem:
    """Individual line item in a transaction receipt."""

    product_id: uuid.UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


@dataclass
class TransactionReceipt:
    """Complete receipt data returned after successful transaction creation."""

    id: uuid.UUID
    items: list[ReceiptItem]
    total_amount: Decimal
    discount_amount: Decimal
    payment_method: PaymentMethod
    cashier_name: str
    created_at: datetime


@dataclass
class TransactionItemInput:
    """Input data for a single transaction line item."""

    product_id: uuid.UUID
    quantity: int


class TransactionService:
    """Service for POS transaction processing and history retrieval.

    Handles transaction creation with full validation (stock availability,
    discount limits), atomic processing (transaction + items + stock decrement),
    and role-scoped transaction listing.
    """

    def __init__(
        self,
        txn_repo: TransactionRepositoryInterface,
        product_repo: ProductRepositoryInterface,
    ) -> None:
        """Initialize TransactionService with required repository dependencies.

        Args:
            txn_repo: Repository for transaction data access operations.
            product_repo: Repository for product data access operations.
        """
        self._txn_repo = txn_repo
        self._product_repo = product_repo

    async def create_transaction(
        self,
        cashier_id: uuid.UUID,
        items: list[TransactionItemInput],
        payment_method: PaymentMethod,
        discount_type: Optional[DiscountType] = None,
        discount_value: Optional[Decimal] = None,
    ) -> TransactionReceipt:
        """Create a new transaction with full validation and atomic processing.

        Validates all products exist and are active, checks stock availability,
        calculates discount, and atomically creates the transaction with items
        and stock decrements.

        Args:
            cashier_id: UUID of the cashier processing the transaction.
            items: List of TransactionItemInput with product_id and quantity.
            payment_method: Payment method used for the transaction.
            discount_type: Optional discount type (percentage or fixed).
            discount_value: Optional discount value (percentage 1-100 or fixed amount).

        Returns:
            TransactionReceipt with complete receipt data.

        Raises:
            ValidationException: If items list is empty, products don't exist,
                products are inactive, stock is insufficient, or discount is invalid.
        """
        # Validate items list is not empty
        if not items:
            raise ValidationException(
                message="Transaction must have at least one item",
                errors=[FieldError(field="items", detail="At least one item is required")],
            )

        # Look up all products by ID
        product_ids = [item.product_id for item in items]
        products = {}
        missing_ids: list[str] = []
        inactive_ids: list[str] = []

        for product_id in product_ids:
            product = await self._product_repo.get_by_id(product_id)
            if product is None:
                missing_ids.append(str(product_id))
            elif not product.is_active:
                inactive_ids.append(str(product_id))
            else:
                products[product_id] = product

        if missing_ids:
            raise ValidationException(
                message="Products not found",
                errors=[
                    FieldError(
                        field="items",
                        detail=f"Products not found: {', '.join(missing_ids)}",
                    )
                ],
            )

        if inactive_ids:
            raise ValidationException(
                message="Products are inactive",
                errors=[
                    FieldError(
                        field="items",
                        detail=f"Products are inactive: {', '.join(inactive_ids)}",
                    )
                ],
            )

        # Calculate subtotal (sum of quantity * unit_price for each item)
        subtotal = Decimal("0.00")
        item_details: list[dict] = []

        for item in items:
            product = products[item.product_id]
            item_subtotal = Decimal(str(item.quantity)) * product.price
            subtotal += item_subtotal
            item_details.append(
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": product.price,
                    "subtotal": item_subtotal,
                }
            )

        # Calculate discount amount
        discount_amount = Decimal("0.00")
        if discount_type is not None and discount_value is not None:
            if discount_value < Decimal("0"):
                raise ValidationException(
                    message="Invalid discount value",
                    errors=[
                        FieldError(
                            field="discount_value",
                            detail="Discount value must be non-negative",
                        )
                    ],
                )

            if discount_type == DiscountType.percentage:
                if discount_value > Decimal("100"):
                    raise ValidationException(
                        message="Invalid discount value",
                        errors=[
                            FieldError(
                                field="discount_value",
                                detail="Percentage discount must be between 0 and 100",
                            )
                        ],
                    )
                discount_amount = (subtotal * discount_value / Decimal("100")).quantize(
                    Decimal("0.01")
                )
            elif discount_type == DiscountType.fixed:
                discount_amount = discount_value

        # Validate discount doesn't exceed subtotal
        if discount_amount > subtotal:
            raise ValidationException(
                message="Discount exceeds transaction subtotal",
                errors=[
                    FieldError(
                        field="discount_value",
                        detail="Discount amount cannot exceed the transaction subtotal",
                    )
                ],
            )

        # Validate all items have sufficient stock
        insufficient_stock_ids: list[str] = []
        for item in items:
            product = products[item.product_id]
            if product.stock < item.quantity:
                insufficient_stock_ids.append(str(item.product_id))

        if insufficient_stock_ids:
            raise ValidationException(
                message="Insufficient stock",
                errors=[
                    FieldError(
                        field="items",
                        detail=f"Insufficient stock for products: {', '.join(insufficient_stock_ids)}",
                    )
                ],
            )

        # Calculate total amount (subtotal - discount)
        total_amount = subtotal - discount_amount

        # Atomically create transaction + items + decrement stock
        transaction = await self._txn_repo.create(
            cashier_id=cashier_id,
            total_amount=total_amount,
            discount_amount=discount_amount,
            payment_method=payment_method,
            items=item_details,
        )

        # Build receipt items with product names
        receipt_items: list[ReceiptItem] = []
        for detail in item_details:
            product = products[detail["product_id"]]
            receipt_items.append(
                ReceiptItem(
                    product_id=detail["product_id"],
                    product_name=product.name,
                    quantity=detail["quantity"],
                    unit_price=detail["unit_price"],
                    subtotal=detail["subtotal"],
                )
            )

        # Get cashier name from the user repository
        # The transaction has the cashier relationship loaded
        cashier_name = ""
        if hasattr(transaction, "cashier") and transaction.cashier is not None:
            cashier_name = transaction.cashier.full_name
        else:
            # Fallback: look up the user via product repo's session isn't ideal,
            # but the transaction should have the cashier loaded via relationship
            cashier_name = "Unknown"

        return TransactionReceipt(
            id=transaction.id,
            items=receipt_items,
            total_amount=total_amount,
            discount_amount=discount_amount,
            payment_method=payment_method,
            cashier_name=cashier_name,
            created_at=transaction.created_at,
        )

    async def list_transactions(
        self,
        user: User,
        filters: TransactionFilters,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """List transactions with role-scoped access and pagination.

        Staff users can only see their own transactions. Admin users can
        see all transactions with optional filtering.

        Args:
            user: The authenticated user making the request.
            filters: TransactionFilters with optional criteria.
            pagination: Pagination parameters (page, page_size).

        Returns:
            PaginatedResult containing matching transactions and total count.
        """
        # Apply role-based scoping
        if user.role == UserRole.staff:
            filters.user_scope = user.id

        # Admin users have no user_scope restriction (can see all)
        # Additional filters (cashier_id, payment_method, date_from, date_to)
        # are passed through as-is

        return await self._txn_repo.list(filters=filters, pagination=pagination)

    async def get_transaction(
        self,
        transaction_id: uuid.UUID,
        user: User,
    ) -> Transaction:
        """Retrieve a single transaction by ID with role-scoped access.

        Staff users can only access their own transactions. Admin users
        can access any transaction.

        Args:
            transaction_id: The UUID of the transaction to retrieve.
            user: The authenticated user making the request.

        Returns:
            The Transaction instance.

        Raises:
            NotFoundException: If the transaction does not exist or the user
                lacks access to it.
        """
        transaction = await self._txn_repo.get_by_id(transaction_id)
        if transaction is None:
            raise NotFoundException(message="Transaction not found")

        # Staff can only see their own transactions
        if user.role == UserRole.staff and transaction.cashier_id != user.id:
            raise NotFoundException(message="Transaction not found")

        return transaction

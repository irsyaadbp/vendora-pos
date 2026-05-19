"""Inventory management service.

Provides stock-in, stock-out, and adjustment operations with full
audit trail via inventory logs. Also provides low-stock product
queries and paginated inventory log history.
"""

import uuid

from app.core.config import get_settings
from app.core.dependencies import PaginationParams
from app.core.exceptions import NotFoundException, ValidationException
from app.domain.interfaces import (
    InventoryLogRepositoryInterface,
    PaginatedResult,
    ProductRepositoryInterface,
)
from app.models.product import Product
from app.schemas.common import FieldError
from app.schemas.enums import AdjustmentType


class InventoryService:
    """Service for inventory management operations.

    Handles stock-in, stock-out, and stock adjustment operations with
    validation and audit logging. Also provides low-stock product queries
    and paginated inventory log history per product.
    """

    def __init__(
        self,
        product_repo: ProductRepositoryInterface,
        log_repo: InventoryLogRepositoryInterface,
    ) -> None:
        """Initialize InventoryService with required repository dependencies.

        Args:
            product_repo: Repository for product data access operations.
            log_repo: Repository for inventory log data access operations.
        """
        self._product_repo = product_repo
        self._log_repo = log_repo

    async def stock_in(
        self,
        product_id: uuid.UUID,
        quantity: int,
        user_id: uuid.UUID,
    ) -> Product:
        """Record a stock-in operation, increasing product stock.

        Args:
            product_id: The UUID of the product to stock in.
            quantity: The quantity to add (1 to 999,999).
            user_id: The UUID of the user performing the operation.

        Returns:
            The updated Product instance with increased stock.

        Raises:
            ValidationException: If quantity is outside the allowed range.
            NotFoundException: If the product does not exist.
        """
        self._validate_quantity(quantity)

        product = await self._get_product_or_raise(product_id)

        # Increase stock
        updated_product = await self._product_repo.update_stock(
            product_id, quantity_change=quantity
        )
        if updated_product is None:
            raise NotFoundException(message="Product not found")

        # Create audit log entry
        await self._log_repo.create(
            product_id=product_id,
            user_id=user_id,
            adjustment_type=AdjustmentType.stock_in,
            quantity_change=quantity,
        )

        return updated_product

    async def stock_out(
        self,
        product_id: uuid.UUID,
        quantity: int,
        user_id: uuid.UUID,
    ) -> Product:
        """Record a stock-out operation, decreasing product stock.

        Args:
            product_id: The UUID of the product to stock out.
            quantity: The quantity to remove (1 to 999,999).
            user_id: The UUID of the user performing the operation.

        Returns:
            The updated Product instance with decreased stock.

        Raises:
            ValidationException: If quantity is outside the allowed range
                or would result in negative stock.
            NotFoundException: If the product does not exist.
        """
        self._validate_quantity(quantity)

        product = await self._get_product_or_raise(product_id)

        # Check if stock-out would result in negative stock
        if product.stock < quantity:
            raise ValidationException(
                message="Insufficient stock",
                errors=[
                    FieldError(
                        field="quantity",
                        detail=f"Cannot remove {quantity} units. Current stock is {product.stock}",
                    )
                ],
            )

        # Decrease stock
        updated_product = await self._product_repo.update_stock(
            product_id, quantity_change=-quantity
        )
        if updated_product is None:
            raise NotFoundException(message="Product not found")

        # Create audit log entry
        await self._log_repo.create(
            product_id=product_id,
            user_id=user_id,
            adjustment_type=AdjustmentType.stock_out,
            quantity_change=-quantity,
        )

        return updated_product

    async def adjust_stock(
        self,
        product_id: uuid.UUID,
        new_quantity: int,
        reason: str,
        user_id: uuid.UUID,
    ) -> Product:
        """Adjust product stock to an exact quantity with a mandatory reason.

        Args:
            product_id: The UUID of the product to adjust.
            new_quantity: The target stock quantity (0 to 999,999).
            reason: Mandatory reason for the adjustment (1 to 500 characters).
            user_id: The UUID of the user performing the adjustment.

        Returns:
            The updated Product instance with the new stock quantity.

        Raises:
            ValidationException: If new_quantity is outside the allowed range
                or reason is missing/too long.
            NotFoundException: If the product does not exist.
        """
        # Validate new_quantity range (0 to 999,999)
        errors: list[FieldError] = []

        if new_quantity < 0 or new_quantity > 999_999:
            errors.append(
                FieldError(
                    field="new_quantity",
                    detail="Quantity must be between 0 and 999,999",
                )
            )

        # Validate reason (1 to 500 characters)
        if not reason or not reason.strip():
            errors.append(
                FieldError(
                    field="reason",
                    detail="Reason is required for stock adjustments",
                )
            )
        elif len(reason.strip()) > 500:
            errors.append(
                FieldError(
                    field="reason",
                    detail="Reason must be at most 500 characters",
                )
            )

        if errors:
            raise ValidationException(message="Validation failed", errors=errors)

        product = await self._get_product_or_raise(product_id)

        # Calculate the quantity change from previous to new
        previous_quantity = product.stock
        quantity_change = new_quantity - previous_quantity

        # Update stock to exact quantity
        updated_product = await self._product_repo.update(
            product_id, stock=new_quantity
        )
        if updated_product is None:
            raise NotFoundException(message="Product not found")

        # Create audit log entry with reason
        await self._log_repo.create(
            product_id=product_id,
            user_id=user_id,
            adjustment_type=AdjustmentType.adjustment,
            quantity_change=quantity_change,
            reason=reason.strip(),
        )

        return updated_product

    async def get_low_stock_products(
        self,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """Return products at or below the configured low-stock threshold.

        Uses the LOW_STOCK_THRESHOLD setting (default 10) to determine
        which products are considered low-stock.

        Args:
            pagination: Pagination parameters (page, page_size).

        Returns:
            PaginatedResult containing low-stock products and total count.
        """
        threshold = self._get_low_stock_threshold()

        return await self._product_repo.get_low_stock(
            threshold=threshold,
            pagination=pagination,
        )

    async def get_product_logs(
        self,
        product_id: uuid.UUID,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """Get paginated inventory log history for a specific product.

        Results are sorted by timestamp descending (most recent first).

        Args:
            product_id: The UUID of the product to get logs for.
            pagination: Pagination parameters (page, page_size; default 20, max 100).

        Returns:
            PaginatedResult containing inventory logs and total count.

        Raises:
            NotFoundException: If the product does not exist.
        """
        # Verify product exists
        await self._get_product_or_raise(product_id)

        return await self._log_repo.list_by_product(
            product_id=product_id,
            pagination=pagination,
        )

    # ─── Private Helpers ─────────────────────────────────────────────────

    def _validate_quantity(self, quantity: int) -> None:
        """Validate that quantity is within the allowed range (1 to 999,999).

        Args:
            quantity: The quantity to validate.

        Raises:
            ValidationException: If quantity is outside the allowed range.
        """
        if quantity < 1 or quantity > 999_999:
            raise ValidationException(
                message="Validation failed",
                errors=[
                    FieldError(
                        field="quantity",
                        detail="Quantity must be between 1 and 999,999",
                    )
                ],
            )

    async def _get_product_or_raise(self, product_id: uuid.UUID) -> Product:
        """Retrieve a product by ID or raise NotFoundException.

        Args:
            product_id: The UUID of the product.

        Returns:
            The Product instance.

        Raises:
            NotFoundException: If the product does not exist.
        """
        product = await self._product_repo.get_by_id(product_id)
        if product is None:
            raise NotFoundException(message="Product not found")
        return product

    def _get_low_stock_threshold(self) -> int:
        """Get the low-stock threshold from application settings.

        Returns:
            The configured LOW_STOCK_THRESHOLD value (default 10).
        """
        try:
            settings = get_settings()
            return settings.LOW_STOCK_THRESHOLD
        except SystemExit:
            return 10

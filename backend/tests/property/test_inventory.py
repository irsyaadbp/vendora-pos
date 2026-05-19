"""Property-based tests for inventory management.

Feature: vendora-pos-foundation
Property 26: Stock operation correctness
Property 27: Stock-out rejection on insufficient stock
Property 28: Inventory quantity range validation
Property 29: Inventory adjustment sets exact quantity with audit trail
Property 30: Low-stock threshold correctness

Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7

These tests verify InventoryService behavior using property-based testing
with Hypothesis strategies and AsyncMock for repositories.
"""

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

# Set environment variables before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-property-tests-minimum-length")

from app.core.dependencies import PaginationParams
from app.core.exceptions import ValidationException, NotFoundException
from app.domain.interfaces import PaginatedResult
from app.models.product import Product
from app.schemas.enums import AdjustmentType
from app.services.inventory_service import InventoryService


# --- Strategies ---

# Valid quantity for stock-in/stock-out: 1 to 999,999
valid_quantity_strategy = st.integers(min_value=1, max_value=999_999)

# Invalid quantity for stock-in/stock-out: below 1 or above 999,999
invalid_quantity_strategy = st.one_of(
    st.integers(min_value=-1_000_000, max_value=0),
    st.integers(min_value=1_000_000, max_value=10_000_000),
)

# Valid quantity for adjust_stock: 0 to 999,999
valid_adjust_quantity_strategy = st.integers(min_value=0, max_value=999_999)

# Invalid quantity for adjust_stock: below 0 or above 999,999
invalid_adjust_quantity_strategy = st.one_of(
    st.integers(min_value=-1_000_000, max_value=-1),
    st.integers(min_value=1_000_000, max_value=10_000_000),
)

# Current stock level for a product
stock_strategy = st.integers(min_value=0, max_value=999_999)

# Reason for adjustment (1 to 500 chars)
reason_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Zs"),
        blacklist_characters="\x00\n\r\t",
    ),
    min_size=1,
    max_size=500,
).filter(lambda s: len(s.strip()) > 0)

# Low-stock threshold
threshold_strategy = st.integers(min_value=0, max_value=99_999)

product_id_strategy = st.uuids()
user_id_strategy = st.uuids()


# --- Helpers ---


def _make_mock_product(
    product_id: Optional[uuid.UUID] = None,
    stock: int = 100,
    name: str = "Test Product",
    sku: str = "TST-001",
    is_active: bool = True,
) -> MagicMock:
    """Create a mock Product object with all required attributes."""
    product = MagicMock(spec=Product)
    product.id = product_id or uuid.uuid4()
    product.name = name
    product.sku = sku
    product.barcode = None
    product.price = Decimal("9.99")
    product.stock = stock
    product.category_id = None
    product.is_active = is_active
    product.created_at = datetime.now(timezone.utc)
    product.updated_at = datetime.now(timezone.utc)
    return product


# --- Property 26: Stock operation correctness ---


class TestStockOperationCorrectness:
    """**Validates: Requirements 8.1, 8.2**

    Property 26: Stock operation correctness.
    For any valid stock-in operation with quantity Q on a product with current
    stock S, the resulting stock SHALL equal S + Q. For any valid stock-out
    operation with quantity Q on a product with stock S where Q <= S, the
    resulting stock SHALL equal S - Q. Both operations SHALL create a
    corresponding inventory log entry.
    """

    @given(
        product_id=product_id_strategy,
        user_id=user_id_strategy,
        current_stock=stock_strategy,
        quantity=valid_quantity_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_stock_in_increases_stock_by_quantity(
        self,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        current_stock: int,
        quantity: int,
    ):
        """For any valid stock-in, the product stock increases by exactly Q."""
        product_repo = AsyncMock()
        log_repo = AsyncMock()

        # Setup: product with current_stock
        existing_product = _make_mock_product(product_id=product_id, stock=current_stock)
        product_repo.get_by_id.return_value = existing_product

        # After stock-in, stock should be current_stock + quantity
        expected_stock = current_stock + quantity
        updated_product = _make_mock_product(product_id=product_id, stock=expected_stock)
        product_repo.update_stock.return_value = updated_product

        service = InventoryService(product_repo=product_repo, log_repo=log_repo)

        result = await service.stock_in(
            product_id=product_id, quantity=quantity, user_id=user_id
        )

        # Verify update_stock was called with positive quantity_change
        product_repo.update_stock.assert_called_once_with(
            product_id, quantity_change=quantity
        )

        # Verify result stock equals expected
        assert result.stock == expected_stock

        # Verify audit log was created
        log_repo.create.assert_called_once_with(
            product_id=product_id,
            user_id=user_id,
            adjustment_type=AdjustmentType.stock_in,
            quantity_change=quantity,
        )

    @given(
        product_id=product_id_strategy,
        user_id=user_id_strategy,
        current_stock=st.integers(min_value=1, max_value=999_999),
        quantity=valid_quantity_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_stock_out_decreases_stock_by_quantity(
        self,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        current_stock: int,
        quantity: int,
    ):
        """For any valid stock-out where Q <= S, the product stock decreases by exactly Q."""
        # Ensure quantity does not exceed current stock
        assume(quantity <= current_stock)

        product_repo = AsyncMock()
        log_repo = AsyncMock()

        # Setup: product with current_stock
        existing_product = _make_mock_product(product_id=product_id, stock=current_stock)
        product_repo.get_by_id.return_value = existing_product

        # After stock-out, stock should be current_stock - quantity
        expected_stock = current_stock - quantity
        updated_product = _make_mock_product(product_id=product_id, stock=expected_stock)
        product_repo.update_stock.return_value = updated_product

        service = InventoryService(product_repo=product_repo, log_repo=log_repo)

        result = await service.stock_out(
            product_id=product_id, quantity=quantity, user_id=user_id
        )

        # Verify update_stock was called with negative quantity_change
        product_repo.update_stock.assert_called_once_with(
            product_id, quantity_change=-quantity
        )

        # Verify result stock equals expected
        assert result.stock == expected_stock

        # Verify audit log was created
        log_repo.create.assert_called_once_with(
            product_id=product_id,
            user_id=user_id,
            adjustment_type=AdjustmentType.stock_out,
            quantity_change=-quantity,
        )


# --- Property 27: Stock-out rejection on insufficient stock ---


class TestStockOutRejectionOnInsufficientStock:
    """**Validates: Requirements 8.3**

    Property 27: Stock-out rejection on insufficient stock.
    For any stock-out operation where the requested quantity exceeds the
    product's current stock, the operation SHALL be rejected and the
    product's stock SHALL remain unchanged.
    """

    @given(
        product_id=product_id_strategy,
        user_id=user_id_strategy,
        current_stock=st.integers(min_value=0, max_value=999_998),
        quantity=valid_quantity_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_stock_out_rejected_when_quantity_exceeds_stock(
        self,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        current_stock: int,
        quantity: int,
    ):
        """For any stock-out where Q > S, the operation is rejected without modifying stock."""
        # Ensure quantity exceeds current stock
        assume(quantity > current_stock)

        product_repo = AsyncMock()
        log_repo = AsyncMock()

        # Setup: product with current_stock
        existing_product = _make_mock_product(product_id=product_id, stock=current_stock)
        product_repo.get_by_id.return_value = existing_product

        service = InventoryService(product_repo=product_repo, log_repo=log_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.stock_out(
                product_id=product_id, quantity=quantity, user_id=user_id
            )

        # Verify error message indicates insufficient stock
        assert "insufficient" in exc_info.value.message.lower() or "stock" in exc_info.value.message.lower()

        # Verify stock was NOT modified
        product_repo.update_stock.assert_not_called()

        # Verify no audit log was created
        log_repo.create.assert_not_called()


# --- Property 28: Inventory quantity range validation ---


class TestInventoryQuantityRangeValidation:
    """**Validates: Requirements 8.4**

    Property 28: Inventory quantity range validation.
    For any stock-in or stock-out operation with a quantity less than 1 or
    greater than 999,999, the operation SHALL be rejected with a validation error.
    For adjust_stock, quantities must be 0-999,999.
    """

    @given(
        product_id=product_id_strategy,
        user_id=user_id_strategy,
        invalid_quantity=invalid_quantity_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_stock_in_rejects_invalid_quantity(
        self,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        invalid_quantity: int,
    ):
        """For any stock-in with quantity < 1 or > 999,999, raises ValidationException."""
        product_repo = AsyncMock()
        log_repo = AsyncMock()

        service = InventoryService(product_repo=product_repo, log_repo=log_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.stock_in(
                product_id=product_id, quantity=invalid_quantity, user_id=user_id
            )

        # Verify error references quantity field
        assert any("quantity" in e.field for e in exc_info.value.errors)

        # Verify no stock modification occurred
        product_repo.update_stock.assert_not_called()
        log_repo.create.assert_not_called()

    @given(
        product_id=product_id_strategy,
        user_id=user_id_strategy,
        invalid_quantity=invalid_quantity_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_stock_out_rejects_invalid_quantity(
        self,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        invalid_quantity: int,
    ):
        """For any stock-out with quantity < 1 or > 999,999, raises ValidationException."""
        product_repo = AsyncMock()
        log_repo = AsyncMock()

        service = InventoryService(product_repo=product_repo, log_repo=log_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.stock_out(
                product_id=product_id, quantity=invalid_quantity, user_id=user_id
            )

        # Verify error references quantity field
        assert any("quantity" in e.field for e in exc_info.value.errors)

        # Verify no stock modification occurred
        product_repo.update_stock.assert_not_called()
        log_repo.create.assert_not_called()

    @given(
        product_id=product_id_strategy,
        user_id=user_id_strategy,
        invalid_quantity=invalid_adjust_quantity_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_adjust_stock_rejects_invalid_quantity(
        self,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        invalid_quantity: int,
    ):
        """For any adjust_stock with new_quantity < 0 or > 999,999, raises ValidationException."""
        product_repo = AsyncMock()
        log_repo = AsyncMock()

        service = InventoryService(product_repo=product_repo, log_repo=log_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.adjust_stock(
                product_id=product_id,
                new_quantity=invalid_quantity,
                reason="Valid reason for adjustment",
                user_id=user_id,
            )

        # Verify error references new_quantity field
        assert any("new_quantity" in e.field for e in exc_info.value.errors)

        # Verify no stock modification occurred
        product_repo.update.assert_not_called()
        log_repo.create.assert_not_called()


# --- Property 29: Inventory adjustment sets exact quantity with audit trail ---


class TestInventoryAdjustmentSetsExactQuantity:
    """**Validates: Requirements 8.5**

    Property 29: Inventory adjustment sets exact quantity with audit trail.
    For any inventory adjustment specifying a new quantity (0-999,999) and a
    reason (1-500 chars), the product stock SHALL be set to exactly the specified
    quantity, and the log entry SHALL record the quantity change, performing user,
    reason, and timestamp.
    """

    @given(
        product_id=product_id_strategy,
        user_id=user_id_strategy,
        current_stock=stock_strategy,
        new_quantity=valid_adjust_quantity_strategy,
        reason=reason_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_adjust_stock_sets_exact_quantity(
        self,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        current_stock: int,
        new_quantity: int,
        reason: str,
    ):
        """For any valid adjustment, stock is set to exactly new_quantity."""
        product_repo = AsyncMock()
        log_repo = AsyncMock()

        # Setup: product with current_stock
        existing_product = _make_mock_product(product_id=product_id, stock=current_stock)
        product_repo.get_by_id.return_value = existing_product

        # After adjustment, stock should be new_quantity
        updated_product = _make_mock_product(product_id=product_id, stock=new_quantity)
        product_repo.update.return_value = updated_product

        service = InventoryService(product_repo=product_repo, log_repo=log_repo)

        result = await service.adjust_stock(
            product_id=product_id,
            new_quantity=new_quantity,
            reason=reason,
            user_id=user_id,
        )

        # Verify repo.update was called with exact new stock
        product_repo.update.assert_called_once_with(product_id, stock=new_quantity)

        # Verify result stock equals new_quantity
        assert result.stock == new_quantity

        # Verify audit log was created with correct data
        expected_quantity_change = new_quantity - current_stock
        log_repo.create.assert_called_once_with(
            product_id=product_id,
            user_id=user_id,
            adjustment_type=AdjustmentType.adjustment,
            quantity_change=expected_quantity_change,
            reason=reason.strip(),
        )

    @given(
        product_id=product_id_strategy,
        user_id=user_id_strategy,
        current_stock=stock_strategy,
        new_quantity=valid_adjust_quantity_strategy,
        reason=reason_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_adjust_stock_logs_correct_quantity_change(
        self,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        current_stock: int,
        new_quantity: int,
        reason: str,
    ):
        """For any adjustment, the log records quantity_change = new_quantity - previous_quantity."""
        product_repo = AsyncMock()
        log_repo = AsyncMock()

        existing_product = _make_mock_product(product_id=product_id, stock=current_stock)
        product_repo.get_by_id.return_value = existing_product

        updated_product = _make_mock_product(product_id=product_id, stock=new_quantity)
        product_repo.update.return_value = updated_product

        service = InventoryService(product_repo=product_repo, log_repo=log_repo)

        await service.adjust_stock(
            product_id=product_id,
            new_quantity=new_quantity,
            reason=reason,
            user_id=user_id,
        )

        # Extract the quantity_change from the log creation call
        log_call_kwargs = log_repo.create.call_args[1]
        logged_quantity_change = log_call_kwargs["quantity_change"]

        # quantity_change should be the difference
        expected_change = new_quantity - current_stock
        assert logged_quantity_change == expected_change, (
            f"Expected quantity_change={expected_change} "
            f"(new={new_quantity} - old={current_stock}), "
            f"got {logged_quantity_change}"
        )


# --- Property 30: Low-stock threshold correctness ---


class TestLowStockThresholdCorrectness:
    """**Validates: Requirements 8.6, 8.7, 8.8**

    Property 30: Low-stock threshold correctness.
    For any product and any configured low-stock threshold T, products at or
    below the threshold are flagged as low-stock.
    """

    @given(
        threshold=threshold_strategy,
        page=st.integers(min_value=1, max_value=10),
        page_size=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_get_low_stock_uses_configured_threshold(
        self,
        threshold: int,
        page: int,
        page_size: int,
    ):
        """For any threshold T, get_low_stock_products queries with that threshold."""
        product_repo = AsyncMock()
        log_repo = AsyncMock()

        # Return empty result for simplicity
        product_repo.get_low_stock.return_value = PaginatedResult(items=[], total_count=0)

        service = InventoryService(product_repo=product_repo, log_repo=log_repo)

        pagination = PaginationParams(page=page, page_size=page_size)

        # Patch get_settings to return our custom threshold
        with patch("app.services.inventory_service.get_settings") as mock_settings:
            mock_settings_instance = MagicMock()
            mock_settings_instance.LOW_STOCK_THRESHOLD = threshold
            mock_settings.return_value = mock_settings_instance

            await service.get_low_stock_products(pagination=pagination)

        # Verify the repository was called with the correct threshold
        product_repo.get_low_stock.assert_called_once_with(
            threshold=threshold,
            pagination=pagination,
        )

    @given(
        threshold=threshold_strategy,
        stock_levels=st.lists(
            st.integers(min_value=0, max_value=999_999),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_low_stock_flag_correctness(
        self,
        threshold: int,
        stock_levels: list[int],
    ):
        """For any set of products and threshold T, only products with stock <= T
        should be in the low-stock result set."""
        product_repo = AsyncMock()
        log_repo = AsyncMock()

        # Create mock products with various stock levels
        all_products = [
            _make_mock_product(stock=stock_level)
            for stock_level in stock_levels
        ]

        # Filter to only those at or below threshold (simulating repo behavior)
        low_stock_products = [p for p in all_products if p.stock <= threshold]

        product_repo.get_low_stock.return_value = PaginatedResult(
            items=low_stock_products, total_count=len(low_stock_products)
        )

        service = InventoryService(product_repo=product_repo, log_repo=log_repo)

        pagination = PaginationParams(page=1, page_size=100)

        with patch("app.services.inventory_service.get_settings") as mock_settings:
            mock_settings_instance = MagicMock()
            mock_settings_instance.LOW_STOCK_THRESHOLD = threshold
            mock_settings.return_value = mock_settings_instance

            result = await service.get_low_stock_products(pagination=pagination)

        # All returned products must have stock <= threshold
        for product in result.items:
            assert product.stock <= threshold, (
                f"Product with stock={product.stock} should not be in "
                f"low-stock list (threshold={threshold})"
            )

        # Count of low-stock products should match expected
        expected_count = sum(1 for s in stock_levels if s <= threshold)
        assert result.total_count == expected_count

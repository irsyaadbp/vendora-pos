"""Unit tests for InventoryService."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.dependencies import PaginationParams
from app.core.exceptions import NotFoundException, ValidationException
from app.domain.interfaces import (
    InventoryLogRepositoryInterface,
    PaginatedResult,
    ProductRepositoryInterface,
)
from app.schemas.enums import AdjustmentType
from app.services.inventory_service import InventoryService


# --- Helpers ---


def _make_product(
    product_id: Optional[uuid.UUID] = None,
    name: str = "Test Product",
    sku: str = "SKU-001",
    stock: int = 50,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock Product object."""
    product = MagicMock()
    product.id = product_id or uuid.uuid4()
    product.name = name
    product.sku = sku
    product.stock = stock
    product.is_active = is_active
    product.created_at = datetime.now(timezone.utc)
    product.updated_at = datetime.now(timezone.utc)
    return product


def _make_inventory_log(
    product_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    adjustment_type: AdjustmentType = AdjustmentType.stock_in,
    quantity_change: int = 10,
    reason: Optional[str] = None,
) -> MagicMock:
    """Create a mock InventoryLog object."""
    log = MagicMock()
    log.id = uuid.uuid4()
    log.product_id = product_id or uuid.uuid4()
    log.user_id = user_id or uuid.uuid4()
    log.adjustment_type = adjustment_type
    log.quantity_change = quantity_change
    log.reason = reason
    log.created_at = datetime.now(timezone.utc)
    return log


def _create_service(
    product_repo: Optional[AsyncMock] = None,
    log_repo: Optional[AsyncMock] = None,
) -> InventoryService:
    """Create an InventoryService with mock repositories."""
    return InventoryService(
        product_repo=product_repo or AsyncMock(spec=ProductRepositoryInterface),
        log_repo=log_repo or AsyncMock(spec=InventoryLogRepositoryInterface),
    )


# --- Stock In Tests ---


class TestInventoryServiceStockIn:
    """Tests for InventoryService.stock_in()."""

    @pytest.mark.asyncio
    async def test_stock_in_success(self) -> None:
        """Successful stock-in increases product stock and creates log entry."""
        product_id = uuid.uuid4()
        user_id = uuid.uuid4()
        product = _make_product(product_id=product_id, stock=50)
        updated_product = _make_product(product_id=product_id, stock=60)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product
        product_repo.update_stock.return_value = updated_product

        log_repo = AsyncMock(spec=InventoryLogRepositoryInterface)
        log_repo.create.return_value = _make_inventory_log()

        service = _create_service(product_repo=product_repo, log_repo=log_repo)

        result = await service.stock_in(product_id, quantity=10, user_id=user_id)

        assert result == updated_product
        product_repo.update_stock.assert_called_once_with(
            product_id, quantity_change=10
        )
        log_repo.create.assert_called_once_with(
            product_id=product_id,
            user_id=user_id,
            adjustment_type=AdjustmentType.stock_in,
            quantity_change=10,
        )

    @pytest.mark.asyncio
    async def test_stock_in_quantity_zero_raises_validation(self) -> None:
        """Stock-in with quantity 0 raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.stock_in(uuid.uuid4(), quantity=0, user_id=uuid.uuid4())

        assert any(e.field == "quantity" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_stock_in_quantity_negative_raises_validation(self) -> None:
        """Stock-in with negative quantity raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.stock_in(uuid.uuid4(), quantity=-5, user_id=uuid.uuid4())

        assert any(e.field == "quantity" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_stock_in_quantity_exceeds_max_raises_validation(self) -> None:
        """Stock-in with quantity > 999,999 raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.stock_in(uuid.uuid4(), quantity=1_000_000, user_id=uuid.uuid4())

        assert any(e.field == "quantity" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_stock_in_product_not_found_raises_not_found(self) -> None:
        """Stock-in for non-existent product raises NotFoundException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = None

        service = _create_service(product_repo=product_repo)

        with pytest.raises(NotFoundException):
            await service.stock_in(uuid.uuid4(), quantity=10, user_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_stock_in_boundary_quantity_1(self) -> None:
        """Stock-in with minimum valid quantity (1) succeeds."""
        product_id = uuid.uuid4()
        product = _make_product(product_id=product_id, stock=10)
        updated_product = _make_product(product_id=product_id, stock=11)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product
        product_repo.update_stock.return_value = updated_product

        log_repo = AsyncMock(spec=InventoryLogRepositoryInterface)
        log_repo.create.return_value = _make_inventory_log()

        service = _create_service(product_repo=product_repo, log_repo=log_repo)

        result = await service.stock_in(product_id, quantity=1, user_id=uuid.uuid4())

        assert result == updated_product

    @pytest.mark.asyncio
    async def test_stock_in_boundary_quantity_999999(self) -> None:
        """Stock-in with maximum valid quantity (999,999) succeeds."""
        product_id = uuid.uuid4()
        product = _make_product(product_id=product_id, stock=0)
        updated_product = _make_product(product_id=product_id, stock=999_999)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product
        product_repo.update_stock.return_value = updated_product

        log_repo = AsyncMock(spec=InventoryLogRepositoryInterface)
        log_repo.create.return_value = _make_inventory_log()

        service = _create_service(product_repo=product_repo, log_repo=log_repo)

        result = await service.stock_in(product_id, quantity=999_999, user_id=uuid.uuid4())

        assert result == updated_product


# --- Stock Out Tests ---


class TestInventoryServiceStockOut:
    """Tests for InventoryService.stock_out()."""

    @pytest.mark.asyncio
    async def test_stock_out_success(self) -> None:
        """Successful stock-out decreases product stock and creates log entry."""
        product_id = uuid.uuid4()
        user_id = uuid.uuid4()
        product = _make_product(product_id=product_id, stock=50)
        updated_product = _make_product(product_id=product_id, stock=40)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product
        product_repo.update_stock.return_value = updated_product

        log_repo = AsyncMock(spec=InventoryLogRepositoryInterface)
        log_repo.create.return_value = _make_inventory_log()

        service = _create_service(product_repo=product_repo, log_repo=log_repo)

        result = await service.stock_out(product_id, quantity=10, user_id=user_id)

        assert result == updated_product
        product_repo.update_stock.assert_called_once_with(
            product_id, quantity_change=-10
        )
        log_repo.create.assert_called_once_with(
            product_id=product_id,
            user_id=user_id,
            adjustment_type=AdjustmentType.stock_out,
            quantity_change=-10,
        )

    @pytest.mark.asyncio
    async def test_stock_out_insufficient_stock_raises_validation(self) -> None:
        """Stock-out exceeding current stock raises ValidationException."""
        product_id = uuid.uuid4()
        product = _make_product(product_id=product_id, stock=5)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product

        service = _create_service(product_repo=product_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.stock_out(product_id, quantity=10, user_id=uuid.uuid4())

        assert "Insufficient stock" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_stock_out_exact_stock_succeeds(self) -> None:
        """Stock-out equal to current stock succeeds (results in 0 stock)."""
        product_id = uuid.uuid4()
        product = _make_product(product_id=product_id, stock=10)
        updated_product = _make_product(product_id=product_id, stock=0)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product
        product_repo.update_stock.return_value = updated_product

        log_repo = AsyncMock(spec=InventoryLogRepositoryInterface)
        log_repo.create.return_value = _make_inventory_log()

        service = _create_service(product_repo=product_repo, log_repo=log_repo)

        result = await service.stock_out(product_id, quantity=10, user_id=uuid.uuid4())

        assert result == updated_product

    @pytest.mark.asyncio
    async def test_stock_out_quantity_zero_raises_validation(self) -> None:
        """Stock-out with quantity 0 raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.stock_out(uuid.uuid4(), quantity=0, user_id=uuid.uuid4())

        assert any(e.field == "quantity" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_stock_out_quantity_exceeds_max_raises_validation(self) -> None:
        """Stock-out with quantity > 999,999 raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.stock_out(uuid.uuid4(), quantity=1_000_000, user_id=uuid.uuid4())

        assert any(e.field == "quantity" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_stock_out_product_not_found_raises_not_found(self) -> None:
        """Stock-out for non-existent product raises NotFoundException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = None

        service = _create_service(product_repo=product_repo)

        with pytest.raises(NotFoundException):
            await service.stock_out(uuid.uuid4(), quantity=5, user_id=uuid.uuid4())


# --- Adjust Stock Tests ---


class TestInventoryServiceAdjustStock:
    """Tests for InventoryService.adjust_stock()."""

    @pytest.mark.asyncio
    async def test_adjust_stock_success(self) -> None:
        """Successful adjustment sets stock to exact quantity and logs change."""
        product_id = uuid.uuid4()
        user_id = uuid.uuid4()
        product = _make_product(product_id=product_id, stock=50)
        updated_product = _make_product(product_id=product_id, stock=30)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product
        product_repo.update.return_value = updated_product

        log_repo = AsyncMock(spec=InventoryLogRepositoryInterface)
        log_repo.create.return_value = _make_inventory_log()

        service = _create_service(product_repo=product_repo, log_repo=log_repo)

        result = await service.adjust_stock(
            product_id, new_quantity=30, reason="Inventory count correction", user_id=user_id
        )

        assert result == updated_product
        product_repo.update.assert_called_once_with(product_id, stock=30)
        log_repo.create.assert_called_once_with(
            product_id=product_id,
            user_id=user_id,
            adjustment_type=AdjustmentType.adjustment,
            quantity_change=-20,  # 30 - 50 = -20
            reason="Inventory count correction",
        )

    @pytest.mark.asyncio
    async def test_adjust_stock_missing_reason_raises_validation(self) -> None:
        """Adjustment without reason raises ValidationException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        service = _create_service(product_repo=product_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.adjust_stock(
                uuid.uuid4(), new_quantity=10, reason="", user_id=uuid.uuid4()
            )

        assert any(e.field == "reason" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_adjust_stock_whitespace_reason_raises_validation(self) -> None:
        """Adjustment with whitespace-only reason raises ValidationException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        service = _create_service(product_repo=product_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.adjust_stock(
                uuid.uuid4(), new_quantity=10, reason="   ", user_id=uuid.uuid4()
            )

        assert any(e.field == "reason" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_adjust_stock_reason_too_long_raises_validation(self) -> None:
        """Adjustment with reason > 500 chars raises ValidationException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        service = _create_service(product_repo=product_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.adjust_stock(
                uuid.uuid4(), new_quantity=10, reason="A" * 501, user_id=uuid.uuid4()
            )

        assert any(e.field == "reason" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_adjust_stock_negative_quantity_raises_validation(self) -> None:
        """Adjustment with negative quantity raises ValidationException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        service = _create_service(product_repo=product_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.adjust_stock(
                uuid.uuid4(), new_quantity=-1, reason="Test", user_id=uuid.uuid4()
            )

        assert any(e.field == "new_quantity" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_adjust_stock_exceeds_max_raises_validation(self) -> None:
        """Adjustment with quantity > 999,999 raises ValidationException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        service = _create_service(product_repo=product_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.adjust_stock(
                uuid.uuid4(), new_quantity=1_000_000, reason="Test", user_id=uuid.uuid4()
            )

        assert any(e.field == "new_quantity" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_adjust_stock_to_zero_succeeds(self) -> None:
        """Adjustment to 0 stock succeeds."""
        product_id = uuid.uuid4()
        product = _make_product(product_id=product_id, stock=50)
        updated_product = _make_product(product_id=product_id, stock=0)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product
        product_repo.update.return_value = updated_product

        log_repo = AsyncMock(spec=InventoryLogRepositoryInterface)
        log_repo.create.return_value = _make_inventory_log()

        service = _create_service(product_repo=product_repo, log_repo=log_repo)

        result = await service.adjust_stock(
            product_id, new_quantity=0, reason="Cleared stock", user_id=uuid.uuid4()
        )

        assert result == updated_product

    @pytest.mark.asyncio
    async def test_adjust_stock_product_not_found_raises_not_found(self) -> None:
        """Adjustment for non-existent product raises NotFoundException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = None

        service = _create_service(product_repo=product_repo)

        with pytest.raises(NotFoundException):
            await service.adjust_stock(
                uuid.uuid4(), new_quantity=10, reason="Test", user_id=uuid.uuid4()
            )

    @pytest.mark.asyncio
    async def test_adjust_stock_strips_reason(self) -> None:
        """Adjustment strips whitespace from reason before storing."""
        product_id = uuid.uuid4()
        product = _make_product(product_id=product_id, stock=50)
        updated_product = _make_product(product_id=product_id, stock=30)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product
        product_repo.update.return_value = updated_product

        log_repo = AsyncMock(spec=InventoryLogRepositoryInterface)
        log_repo.create.return_value = _make_inventory_log()

        service = _create_service(product_repo=product_repo, log_repo=log_repo)

        await service.adjust_stock(
            product_id, new_quantity=30, reason="  Trimmed reason  ", user_id=uuid.uuid4()
        )

        call_kwargs = log_repo.create.call_args[1]
        assert call_kwargs["reason"] == "Trimmed reason"


# --- Get Low Stock Products Tests ---


class TestInventoryServiceGetLowStockProducts:
    """Tests for InventoryService.get_low_stock_products()."""

    @pytest.mark.asyncio
    async def test_get_low_stock_products_delegates_to_repo(self) -> None:
        """get_low_stock_products delegates to product_repo.get_low_stock."""
        products = [_make_product(stock=5), _make_product(stock=3)]
        paginated_result = PaginatedResult(items=products, total_count=2)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.return_value = paginated_result

        service = _create_service(product_repo=product_repo)
        pagination = PaginationParams(page=1, page_size=20)

        with patch.object(service, "_get_low_stock_threshold", return_value=10):
            result = await service.get_low_stock_products(pagination=pagination)

        assert result == paginated_result
        product_repo.get_low_stock.assert_called_once_with(
            threshold=10, pagination=pagination
        )

    @pytest.mark.asyncio
    async def test_get_low_stock_products_empty_result(self) -> None:
        """get_low_stock_products returns empty result when no products are low."""
        paginated_result = PaginatedResult(items=[], total_count=0)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.return_value = paginated_result

        service = _create_service(product_repo=product_repo)
        pagination = PaginationParams(page=1, page_size=20)

        with patch.object(service, "_get_low_stock_threshold", return_value=10):
            result = await service.get_low_stock_products(pagination=pagination)

        assert result.items == []
        assert result.total_count == 0


# --- Get Product Logs Tests ---


class TestInventoryServiceGetProductLogs:
    """Tests for InventoryService.get_product_logs()."""

    @pytest.mark.asyncio
    async def test_get_product_logs_success(self) -> None:
        """get_product_logs returns paginated logs for existing product."""
        product_id = uuid.uuid4()
        product = _make_product(product_id=product_id)
        logs = [_make_inventory_log(product_id=product_id) for _ in range(3)]
        paginated_result = PaginatedResult(items=logs, total_count=3)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product

        log_repo = AsyncMock(spec=InventoryLogRepositoryInterface)
        log_repo.list_by_product.return_value = paginated_result

        service = _create_service(product_repo=product_repo, log_repo=log_repo)
        pagination = PaginationParams(page=1, page_size=20)

        result = await service.get_product_logs(product_id=product_id, pagination=pagination)

        assert result == paginated_result
        log_repo.list_by_product.assert_called_once_with(
            product_id=product_id, pagination=pagination
        )

    @pytest.mark.asyncio
    async def test_get_product_logs_product_not_found_raises_not_found(self) -> None:
        """get_product_logs for non-existent product raises NotFoundException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = None

        service = _create_service(product_repo=product_repo)
        pagination = PaginationParams(page=1, page_size=20)

        with pytest.raises(NotFoundException):
            await service.get_product_logs(product_id=uuid.uuid4(), pagination=pagination)

    @pytest.mark.asyncio
    async def test_get_product_logs_empty_result(self) -> None:
        """get_product_logs returns empty result when no logs exist."""
        product_id = uuid.uuid4()
        product = _make_product(product_id=product_id)
        paginated_result = PaginatedResult(items=[], total_count=0)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product

        log_repo = AsyncMock(spec=InventoryLogRepositoryInterface)
        log_repo.list_by_product.return_value = paginated_result

        service = _create_service(product_repo=product_repo, log_repo=log_repo)
        pagination = PaginationParams(page=1, page_size=20)

        result = await service.get_product_logs(product_id=product_id, pagination=pagination)

        assert result.items == []
        assert result.total_count == 0

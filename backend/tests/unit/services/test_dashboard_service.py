"""Unit tests for DashboardService."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.core.dependencies import PaginationParams
from app.domain.interfaces import (
    PaginatedResult,
    ProductRepositoryInterface,
    TransactionRepositoryInterface,
    UserRepositoryInterface,
)
from app.schemas.enums import UserRole
from app.services.dashboard_service import (
    DashboardMetrics,
    DashboardService,
    RecentTransaction,
)


# --- Helpers ---


def _make_settings(low_stock_threshold: int = 10) -> MagicMock:
    """Create a mock Settings object."""
    settings = MagicMock(spec=Settings)
    settings.LOW_STOCK_THRESHOLD = low_stock_threshold
    return settings


def _make_transaction(
    total_amount: Decimal = Decimal("100.00"),
    cashier_name: str = "John Doe",
) -> MagicMock:
    """Create a mock Transaction object with cashier relationship."""
    transaction = MagicMock()
    transaction.id = uuid.uuid4()
    transaction.total_amount = total_amount
    transaction.created_at = datetime.now(timezone.utc)
    transaction.cashier = MagicMock()
    transaction.cashier.full_name = cashier_name
    return transaction


def _make_product(
    name: str = "Low Stock Product",
    stock: int = 5,
) -> MagicMock:
    """Create a mock Product object."""
    product = MagicMock()
    product.id = uuid.uuid4()
    product.name = name
    product.stock = stock
    product.is_active = True
    return product


def _create_service(
    txn_repo: Optional[AsyncMock] = None,
    product_repo: Optional[AsyncMock] = None,
    user_repo: Optional[AsyncMock] = None,
    settings: Optional[MagicMock] = None,
) -> DashboardService:
    """Create a DashboardService with mock dependencies."""
    return DashboardService(
        txn_repo=txn_repo or AsyncMock(spec=TransactionRepositoryInterface),
        product_repo=product_repo or AsyncMock(spec=ProductRepositoryInterface),
        user_repo=user_repo or AsyncMock(spec=UserRepositoryInterface),
        settings=settings or _make_settings(),
    )


# --- Tests ---


class TestDashboardServiceGetMetrics:
    """Tests for DashboardService.get_dashboard_metrics()."""

    @pytest.mark.asyncio
    async def test_returns_dashboard_metrics_dataclass(self) -> None:
        """get_dashboard_metrics returns a DashboardMetrics instance."""
        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.return_value = PaginatedResult(
            items=[], total_count=0
        )

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        service = _create_service(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
        )

        result = await service.get_dashboard_metrics()

        assert isinstance(result, DashboardMetrics)
        assert result.today_sales == Decimal("0.00")
        assert result.today_transaction_count == 0
        assert result.low_stock_products == []
        assert result.active_staff_count == 0
        assert result.recent_transactions == []
        assert result.errors == {}

    @pytest.mark.asyncio
    async def test_today_sales_sums_transaction_amounts(self) -> None:
        """today_sales is the sum of all transaction total_amounts for today."""
        txn1 = _make_transaction(total_amount=Decimal("50.00"))
        txn2 = _make_transaction(total_amount=Decimal("75.50"))
        txn3 = _make_transaction(total_amount=Decimal("24.50"))

        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        # First call: today's sales (with date filters)
        # Second call: recent transactions (no date filters)
        txn_repo.list.side_effect = [
            PaginatedResult(items=[txn1, txn2, txn3], total_count=3),
            PaginatedResult(items=[txn1, txn2, txn3], total_count=3),
        ]

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.return_value = PaginatedResult(
            items=[], total_count=0
        )

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        service = _create_service(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
        )

        result = await service.get_dashboard_metrics()

        assert result.today_sales == Decimal("150.00")
        assert result.today_transaction_count == 3

    @pytest.mark.asyncio
    async def test_low_stock_products_returned(self) -> None:
        """low_stock_products contains products at or below threshold."""
        product1 = _make_product(name="Product A", stock=3)
        product2 = _make_product(name="Product B", stock=10)

        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.return_value = PaginatedResult(
            items=[product1, product2], total_count=2
        )

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        service = _create_service(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
        )

        result = await service.get_dashboard_metrics()

        assert len(result.low_stock_products) == 2
        assert result.low_stock_products[0].name == "Product A"
        assert result.low_stock_products[1].name == "Product B"

    @pytest.mark.asyncio
    async def test_active_staff_count(self) -> None:
        """active_staff_count reflects the total_count from user repo."""
        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.return_value = PaginatedResult(
            items=[], total_count=0
        )

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.return_value = PaginatedResult(items=[], total_count=5)

        service = _create_service(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
        )

        result = await service.get_dashboard_metrics()

        assert result.active_staff_count == 5
        # Verify the correct filters were used
        call_args = user_repo.list.call_args
        filters = call_args.kwargs.get("filters") or call_args[0][0]
        assert filters.role == UserRole.staff
        assert filters.is_active is True

    @pytest.mark.asyncio
    async def test_recent_transactions_with_cashier_name(self) -> None:
        """recent_transactions includes cashier full name."""
        txn1 = _make_transaction(
            total_amount=Decimal("200.00"), cashier_name="Alice Smith"
        )
        txn2 = _make_transaction(
            total_amount=Decimal("150.00"), cashier_name="Bob Jones"
        )

        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        # First call: today's sales
        # Second call: recent transactions
        txn_repo.list.side_effect = [
            PaginatedResult(items=[], total_count=0),
            PaginatedResult(items=[txn1, txn2], total_count=2),
        ]

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.return_value = PaginatedResult(
            items=[], total_count=0
        )

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        service = _create_service(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
        )

        result = await service.get_dashboard_metrics()

        assert len(result.recent_transactions) == 2
        assert result.recent_transactions[0].cashier_name == "Alice Smith"
        assert result.recent_transactions[0].total_amount == Decimal("200.00")
        assert result.recent_transactions[1].cashier_name == "Bob Jones"

    @pytest.mark.asyncio
    async def test_recent_transactions_without_cashier_shows_unknown(self) -> None:
        """recent_transactions shows 'Unknown' when cashier is None."""
        txn = MagicMock()
        txn.id = uuid.uuid4()
        txn.total_amount = Decimal("100.00")
        txn.created_at = datetime.now(timezone.utc)
        txn.cashier = None

        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.list.side_effect = [
            PaginatedResult(items=[], total_count=0),
            PaginatedResult(items=[txn], total_count=1),
        ]

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.return_value = PaginatedResult(
            items=[], total_count=0
        )

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        service = _create_service(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
        )

        result = await service.get_dashboard_metrics()

        assert len(result.recent_transactions) == 1
        assert result.recent_transactions[0].cashier_name == "Unknown"


class TestDashboardServicePartialFailures:
    """Tests for graceful partial failure handling."""

    @pytest.mark.asyncio
    async def test_sales_failure_returns_error_indicator(self) -> None:
        """If sales fetch fails, error is recorded but other metrics work."""
        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        # First call (today's sales) raises, second call (recent) succeeds
        txn_repo.list.side_effect = [
            Exception("Database connection error"),
            PaginatedResult(items=[], total_count=0),
        ]

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.return_value = PaginatedResult(
            items=[], total_count=0
        )

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.return_value = PaginatedResult(items=[], total_count=3)

        service = _create_service(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
        )

        result = await service.get_dashboard_metrics()

        assert "today_sales" in result.errors
        assert "today_transaction_count" in result.errors
        # Other metrics still work
        assert result.active_staff_count == 3
        assert result.low_stock_products == []

    @pytest.mark.asyncio
    async def test_low_stock_failure_returns_error_indicator(self) -> None:
        """If low-stock fetch fails, error is recorded but other metrics work."""
        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.side_effect = Exception("Query timeout")

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.return_value = PaginatedResult(items=[], total_count=2)

        service = _create_service(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
        )

        result = await service.get_dashboard_metrics()

        assert "low_stock_products" in result.errors
        # Other metrics still work
        assert result.active_staff_count == 2
        assert result.today_sales == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_staff_count_failure_returns_error_indicator(self) -> None:
        """If staff count fetch fails, error is recorded but other metrics work."""
        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.return_value = PaginatedResult(
            items=[], total_count=0
        )

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.side_effect = Exception("Connection refused")

        service = _create_service(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
        )

        result = await service.get_dashboard_metrics()

        assert "active_staff_count" in result.errors
        # Other metrics still work
        assert result.today_sales == Decimal("0.00")
        assert result.low_stock_products == []

    @pytest.mark.asyncio
    async def test_recent_transactions_failure_returns_error_indicator(self) -> None:
        """If recent transactions fetch fails, error is recorded."""
        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        # First call (today's sales) succeeds, second call (recent) fails
        txn_repo.list.side_effect = [
            PaginatedResult(items=[], total_count=0),
            Exception("Timeout"),
        ]

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.return_value = PaginatedResult(
            items=[], total_count=0
        )

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.return_value = PaginatedResult(items=[], total_count=4)

        service = _create_service(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
        )

        result = await service.get_dashboard_metrics()

        assert "recent_transactions" in result.errors
        # Other metrics still work
        assert result.active_staff_count == 4
        assert result.today_sales == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_all_metrics_fail_returns_all_errors(self) -> None:
        """If all metrics fail, all errors are recorded."""
        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.list.side_effect = Exception("DB down")

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.side_effect = Exception("DB down")

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.side_effect = Exception("DB down")

        service = _create_service(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
        )

        result = await service.get_dashboard_metrics()

        assert "today_sales" in result.errors
        assert "today_transaction_count" in result.errors
        assert "low_stock_products" in result.errors
        assert "active_staff_count" in result.errors
        assert "recent_transactions" in result.errors
        # Default values are preserved
        assert result.today_sales == Decimal("0.00")
        assert result.today_transaction_count == 0
        assert result.low_stock_products == []
        assert result.active_staff_count == 0
        assert result.recent_transactions == []

    @pytest.mark.asyncio
    async def test_uses_configured_low_stock_threshold(self) -> None:
        """The service uses the LOW_STOCK_THRESHOLD from settings."""
        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_low_stock.return_value = PaginatedResult(
            items=[], total_count=0
        )

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        settings = _make_settings(low_stock_threshold=25)

        service = _create_service(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
            settings=settings,
        )

        await service.get_dashboard_metrics()

        # Verify the threshold was passed to get_low_stock
        product_repo.get_low_stock.assert_called_once()
        call_kwargs = product_repo.get_low_stock.call_args.kwargs
        assert call_kwargs.get("threshold") == 25

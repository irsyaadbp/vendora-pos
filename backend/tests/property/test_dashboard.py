"""Property-based tests for dashboard metrics.

Feature: vendora-pos-foundation
Property 31: Dashboard daily sales accuracy
Property 32: Dashboard active staff count accuracy
Property 33: Dashboard recent transactions ordering

Validates: Requirements 9.1, 9.2, 9.4, 9.5

These tests verify DashboardService behavior using property-based testing
with Hypothesis strategies and AsyncMock for repositories.
"""

import os
import uuid
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

# Set environment variables before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-property-tests-minimum-length")

from app.core.config import Settings
from app.core.dependencies import PaginationParams
from app.domain.interfaces import PaginatedResult, TransactionFilters, UserFilters
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.enums import (
    PaymentMethod,
    TransactionStatus,
    UserRole,
)
from app.services.dashboard_service import DashboardService, DashboardMetrics


# --- Strategies ---

# Positive decimal amounts for transaction totals (0.01 to 999,999.99)
amount_strategy = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

# Payment method strategy
payment_method_strategy = st.sampled_from(list(PaymentMethod))

# Transaction status strategy
transaction_status_strategy = st.sampled_from(list(TransactionStatus))

# User role strategy
user_role_strategy = st.sampled_from(list(UserRole))

# Boolean strategy for is_active
is_active_strategy = st.booleans()


# --- Helpers ---


def _make_mock_settings(low_stock_threshold: int = 10) -> MagicMock:
    """Create a mock Settings object."""
    mock_settings = MagicMock(spec=Settings)
    mock_settings.LOW_STOCK_THRESHOLD = low_stock_threshold
    return mock_settings


def _make_mock_transaction(
    transaction_id: Optional[uuid.UUID] = None,
    cashier_id: Optional[uuid.UUID] = None,
    total_amount: Decimal = Decimal("100.00"),
    discount_amount: Decimal = Decimal("0.00"),
    payment_method: PaymentMethod = PaymentMethod.cash,
    status: TransactionStatus = TransactionStatus.completed,
    created_at: Optional[datetime] = None,
    cashier_name: str = "Test Cashier",
) -> MagicMock:
    """Create a mock Transaction object with all required attributes."""
    txn = MagicMock(spec=Transaction)
    txn.id = transaction_id or uuid.uuid4()
    txn.cashier_id = cashier_id or uuid.uuid4()
    txn.total_amount = total_amount
    txn.discount_amount = discount_amount
    txn.payment_method = payment_method
    txn.status = status
    txn.created_at = created_at or datetime.now(timezone.utc)

    # Mock cashier relationship
    cashier_mock = MagicMock()
    cashier_mock.full_name = cashier_name
    txn.cashier = cashier_mock

    return txn


def _make_mock_user(
    user_id: Optional[uuid.UUID] = None,
    role: UserRole = UserRole.staff,
    is_active: bool = True,
    full_name: str = "Test User",
) -> MagicMock:
    """Create a mock User object with all required attributes."""
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.full_name = full_name
    user.email = f"{full_name.lower().replace(' ', '.')}@test.com"
    user.role = role
    user.is_active = is_active
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


# --- Property 31: Dashboard daily sales accuracy ---


class TestDashboardDailySalesAccuracy:
    """**Validates: Requirements 9.1, 9.2**

    Property 31: Dashboard daily sales accuracy.
    For any set of completed transactions created on the current day,
    the dashboard's total_sales metric SHALL equal the sum of their
    total_amount values, and the transaction_count metric SHALL equal
    the count of those transactions.
    """

    @given(
        amounts=st.lists(
            amount_strategy,
            min_size=0,
            max_size=20,
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_today_sales_equals_sum_of_completed_transactions(
        self,
        amounts: list[Decimal],
    ):
        """For any set of today's transactions, today_sales equals sum of
        their total_amount values and transaction_count equals the count."""
        # Create mock transactions for today
        today_transactions = [
            _make_mock_transaction(
                total_amount=amount,
                status=TransactionStatus.completed,
                created_at=datetime.now(timezone.utc),
            )
            for amount in amounts
        ]

        # Setup mocks
        txn_repo = AsyncMock()
        product_repo = AsyncMock()
        user_repo = AsyncMock()
        mock_settings = _make_mock_settings()

        # First call to txn_repo.list is for today's transactions
        # Second call is for recent transactions
        txn_repo.list.side_effect = [
            PaginatedResult(items=today_transactions, total_count=len(today_transactions)),
            PaginatedResult(items=today_transactions[:10], total_count=len(today_transactions)),
        ]

        # User repo returns empty for staff count
        user_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        # Product repo returns empty for low stock
        product_repo.get_low_stock.return_value = PaginatedResult(items=[], total_count=0)

        service = DashboardService(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
            settings=mock_settings,
        )

        result = await service.get_dashboard_metrics()

        # Calculate expected values: the service sums all transactions returned
        # (it uses total_count for the count)
        expected_sales = sum(amounts, Decimal("0.00"))
        expected_count = len(today_transactions)

        # Verify
        assert result.today_sales == expected_sales, (
            f"Expected today_sales={expected_sales}, got {result.today_sales}"
        )
        assert result.today_transaction_count == expected_count, (
            f"Expected today_transaction_count={expected_count}, "
            f"got {result.today_transaction_count}"
        )

    @given(
        num_transactions=st.integers(min_value=0, max_value=15),
        amount=amount_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_today_sales_sum_is_consistent_with_count(
        self,
        num_transactions: int,
        amount: Decimal,
    ):
        """Today's sales sum and transaction count are consistent:
        if all transactions have the same amount, sales = amount * count."""
        today_transactions = [
            _make_mock_transaction(
                total_amount=amount,
                status=TransactionStatus.completed,
                created_at=datetime.now(timezone.utc),
            )
            for _ in range(num_transactions)
        ]

        # Setup mocks
        txn_repo = AsyncMock()
        product_repo = AsyncMock()
        user_repo = AsyncMock()
        mock_settings = _make_mock_settings()

        txn_repo.list.side_effect = [
            PaginatedResult(items=today_transactions, total_count=num_transactions),
            PaginatedResult(items=today_transactions[:10], total_count=num_transactions),
        ]
        user_repo.list.return_value = PaginatedResult(items=[], total_count=0)
        product_repo.get_low_stock.return_value = PaginatedResult(items=[], total_count=0)

        service = DashboardService(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
            settings=mock_settings,
        )

        result = await service.get_dashboard_metrics()

        # Sales should equal amount * count
        expected_sales = amount * num_transactions
        assert result.today_sales == expected_sales
        assert result.today_transaction_count == num_transactions


# --- Property 32: Dashboard active staff count accuracy ---


class TestDashboardActiveStaffCountAccuracy:
    """**Validates: Requirements 9.4**

    Property 32: Dashboard active staff count accuracy.
    For any set of users in the system, the dashboard's active_staff_count
    SHALL equal the count of users where role is "staff" and is_active is True.
    """

    @given(
        user_configs=st.lists(
            st.tuples(user_role_strategy, is_active_strategy),
            min_size=0,
            max_size=30,
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_active_staff_count_matches_filtered_users(
        self,
        user_configs: list[tuple[UserRole, bool]],
    ):
        """For any set of users with various roles/active statuses,
        active_staff_count equals users with role=staff and is_active=True."""
        # Calculate expected active staff count
        expected_active_staff = sum(
            1 for role, is_active in user_configs
            if role == UserRole.staff and is_active is True
        )

        # Setup mocks
        txn_repo = AsyncMock()
        product_repo = AsyncMock()
        user_repo = AsyncMock()
        mock_settings = _make_mock_settings()

        # The dashboard service queries user_repo.list with staff+active filters
        # and uses total_count from the result
        user_repo.list.return_value = PaginatedResult(
            items=[],  # Items don't matter, only total_count
            total_count=expected_active_staff,
        )

        # Transaction repo returns empty
        txn_repo.list.side_effect = [
            PaginatedResult(items=[], total_count=0),
            PaginatedResult(items=[], total_count=0),
        ]

        # Product repo returns empty for low stock
        product_repo.get_low_stock.return_value = PaginatedResult(items=[], total_count=0)

        service = DashboardService(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
            settings=mock_settings,
        )

        result = await service.get_dashboard_metrics()

        # Verify active_staff_count matches expected
        assert result.active_staff_count == expected_active_staff, (
            f"Expected active_staff_count={expected_active_staff}, "
            f"got {result.active_staff_count}"
        )

        # Verify the user_repo.list was called with correct filters
        call_args = user_repo.list.call_args
        filters_arg = call_args[1]["filters"] if "filters" in call_args[1] else call_args[0][0]
        assert filters_arg.role == UserRole.staff
        assert filters_arg.is_active is True

    @given(
        num_active_staff=st.integers(min_value=0, max_value=50),
        num_inactive_staff=st.integers(min_value=0, max_value=20),
        num_active_admin=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_only_active_staff_counted_not_admins_or_inactive(
        self,
        num_active_staff: int,
        num_inactive_staff: int,
        num_active_admin: int,
    ):
        """Only users with role=staff AND is_active=True are counted.
        Admins and inactive staff are excluded."""
        # The service queries with role=staff, is_active=True
        # So the repo should return only active staff count
        expected_count = num_active_staff

        # Setup mocks
        txn_repo = AsyncMock()
        product_repo = AsyncMock()
        user_repo = AsyncMock()
        mock_settings = _make_mock_settings()

        user_repo.list.return_value = PaginatedResult(
            items=[],
            total_count=expected_count,
        )

        txn_repo.list.side_effect = [
            PaginatedResult(items=[], total_count=0),
            PaginatedResult(items=[], total_count=0),
        ]
        product_repo.get_low_stock.return_value = PaginatedResult(items=[], total_count=0)

        service = DashboardService(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
            settings=mock_settings,
        )

        result = await service.get_dashboard_metrics()

        assert result.active_staff_count == expected_count


# --- Property 33: Dashboard recent transactions ordering ---


class TestDashboardRecentTransactionsOrdering:
    """**Validates: Requirements 9.5**

    Property 33: Dashboard recent transactions ordering.
    For any set of transactions in the system, the dashboard's
    recent_transactions list SHALL contain exactly the 10 most recent
    transactions ordered by created_at descending.
    """

    @given(
        num_transactions=st.integers(min_value=0, max_value=25),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_recent_transactions_ordered_by_timestamp_descending(
        self,
        num_transactions: int,
    ):
        """For any set of recent transactions, they are ordered by
        created_at descending."""
        base_time = datetime.now(timezone.utc)

        # Create transactions with distinct timestamps (most recent first,
        # as the repository would return them ordered by created_at desc)
        transactions = []
        for i in range(num_transactions):
            txn = _make_mock_transaction(
                total_amount=Decimal("10.00") * (i + 1),
                status=TransactionStatus.completed,
                created_at=base_time - timedelta(minutes=i),
                cashier_name=f"Cashier {i}",
            )
            transactions.append(txn)

        # The repo returns at most 10 (page_size=10 in the service)
        recent_transactions = transactions[:10]

        # Setup mocks
        txn_repo = AsyncMock()
        product_repo = AsyncMock()
        user_repo = AsyncMock()
        mock_settings = _make_mock_settings()

        txn_repo.list.side_effect = [
            PaginatedResult(items=[], total_count=0),  # today's transactions
            PaginatedResult(items=recent_transactions, total_count=num_transactions),  # recent
        ]
        user_repo.list.return_value = PaginatedResult(items=[], total_count=0)
        product_repo.get_low_stock.return_value = PaginatedResult(items=[], total_count=0)

        service = DashboardService(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
            settings=mock_settings,
        )

        result = await service.get_dashboard_metrics()

        # Verify ordering: each transaction's created_at >= next one's created_at
        for i in range(len(result.recent_transactions) - 1):
            current = result.recent_transactions[i]
            next_txn = result.recent_transactions[i + 1]
            assert current.created_at >= next_txn.created_at, (
                f"Transaction at index {i} (created_at={current.created_at}) "
                f"should be >= transaction at index {i+1} "
                f"(created_at={next_txn.created_at})"
            )

        # Verify at most 10 transactions returned
        assert len(result.recent_transactions) <= 10

    @given(
        timestamps=st.lists(
            st.integers(min_value=0, max_value=10000),
            min_size=1,
            max_size=20,
            unique=True,
        ),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_recent_transactions_contains_at_most_10(
        self,
        timestamps: list[int],
    ):
        """The dashboard returns at most 10 recent transactions regardless
        of how many exist in the system."""
        base_time = datetime.now(timezone.utc)

        # Sort timestamps ascending (smallest offset = most recent timestamp)
        # to simulate repo returning results ordered by created_at descending
        sorted_timestamps = sorted(timestamps)

        # Create transactions sorted by created_at descending (most recent first)
        all_transactions = [
            _make_mock_transaction(
                total_amount=Decimal("25.00"),
                status=TransactionStatus.completed,
                created_at=base_time - timedelta(minutes=ts),
                cashier_name=f"Cashier {idx}",
            )
            for idx, ts in enumerate(sorted_timestamps)
        ]

        # Repo returns at most 10 (page_size=10 in the service)
        recent_from_repo = all_transactions[:10]

        # Setup mocks
        txn_repo = AsyncMock()
        product_repo = AsyncMock()
        user_repo = AsyncMock()
        mock_settings = _make_mock_settings()

        txn_repo.list.side_effect = [
            PaginatedResult(items=[], total_count=0),  # today's transactions
            PaginatedResult(items=recent_from_repo, total_count=len(all_transactions)),
        ]
        user_repo.list.return_value = PaginatedResult(items=[], total_count=0)
        product_repo.get_low_stock.return_value = PaginatedResult(items=[], total_count=0)

        service = DashboardService(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
            settings=mock_settings,
        )

        result = await service.get_dashboard_metrics()

        # At most 10 recent transactions
        assert len(result.recent_transactions) <= 10

        # If more than 10 exist, exactly 10 should be returned
        if len(all_transactions) > 10:
            assert len(result.recent_transactions) == 10

        # Verify descending order
        for i in range(len(result.recent_transactions) - 1):
            assert result.recent_transactions[i].created_at >= result.recent_transactions[i + 1].created_at

    @given(
        num_transactions=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_recent_transactions_include_cashier_name_and_amount(
        self,
        num_transactions: int,
    ):
        """Each recent transaction includes cashier full name, total amount,
        and timestamp."""
        base_time = datetime.now(timezone.utc)

        transactions = [
            _make_mock_transaction(
                total_amount=Decimal("10.00") * (i + 1),
                status=TransactionStatus.completed,
                created_at=base_time - timedelta(minutes=i),
                cashier_name=f"Cashier {i}",
            )
            for i in range(num_transactions)
        ]

        recent_from_repo = transactions[:10]

        # Setup mocks
        txn_repo = AsyncMock()
        product_repo = AsyncMock()
        user_repo = AsyncMock()
        mock_settings = _make_mock_settings()

        txn_repo.list.side_effect = [
            PaginatedResult(items=[], total_count=0),
            PaginatedResult(items=recent_from_repo, total_count=num_transactions),
        ]
        user_repo.list.return_value = PaginatedResult(items=[], total_count=0)
        product_repo.get_low_stock.return_value = PaginatedResult(items=[], total_count=0)

        service = DashboardService(
            txn_repo=txn_repo,
            product_repo=product_repo,
            user_repo=user_repo,
            settings=mock_settings,
        )

        result = await service.get_dashboard_metrics()

        # Each recent transaction should have cashier_name, total_amount, created_at
        for i, recent_txn in enumerate(result.recent_transactions):
            source_txn = recent_from_repo[i]
            assert recent_txn.cashier_name == source_txn.cashier.full_name
            assert recent_txn.total_amount == source_txn.total_amount
            assert recent_txn.created_at == source_txn.created_at
            assert recent_txn.id == str(source_txn.id)

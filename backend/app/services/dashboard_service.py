"""Dashboard metrics aggregation service.

Provides aggregated business metrics for the admin dashboard including
today's sales, transaction count, low-stock products, active staff count,
and recent transactions. Each metric is fetched independently so partial
failures don't block the entire response.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from decimal import Decimal

from app.core.config import Settings
from app.core.dependencies import PaginationParams
from app.domain.interfaces import (
    ProductRepositoryInterface,
    TransactionFilters,
    TransactionRepositoryInterface,
    UserFilters,
    UserRepositoryInterface,
)
from app.models.product import Product
from app.schemas.enums import UserRole

logger = logging.getLogger(__name__)


@dataclass
class RecentTransaction:
    """A recent transaction with cashier name for dashboard display."""

    id: str
    total_amount: Decimal
    cashier_name: str
    created_at: datetime


@dataclass
class DashboardMetrics:
    """Aggregated dashboard metrics returned by DashboardService.

    Attributes:
        today_sales: Total sales amount for the current day.
        today_transaction_count: Number of transactions today.
        low_stock_products: Products at or below the low-stock threshold.
        active_staff_count: Number of active staff users.
        recent_transactions: 10 most recent transactions with cashier name.
        errors: Metric name -> error message for any failed metrics.
    """

    today_sales: Decimal = Decimal("0.00")
    today_transaction_count: int = 0
    low_stock_products: list[Product] = field(default_factory=list)
    active_staff_count: int = 0
    recent_transactions: list[RecentTransaction] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


class DashboardService:
    """Service for aggregating admin dashboard metrics.

    Fetches each metric independently so that partial failures don't
    block the entire dashboard response. Failed metrics are reported
    in the errors dict while successfully retrieved metrics are still returned.
    """

    def __init__(
        self,
        txn_repo: TransactionRepositoryInterface,
        product_repo: ProductRepositoryInterface,
        user_repo: UserRepositoryInterface,
        settings: Settings,
    ) -> None:
        """Initialize DashboardService with required repository dependencies.

        Args:
            txn_repo: Repository for transaction data access operations.
            product_repo: Repository for product data access operations.
            user_repo: Repository for user data access operations.
            settings: Application settings for configuration values.
        """
        self._txn_repo = txn_repo
        self._product_repo = product_repo
        self._user_repo = user_repo
        self._settings = settings

    async def get_dashboard_metrics(self) -> DashboardMetrics:
        """Retrieve all dashboard metrics with graceful partial failure handling.

        Each metric is fetched independently. If any metric fails, the error
        is recorded in the errors dict and remaining metrics are still returned.

        Defines "current day" as 00:00:00 to 23:59:59 in server timezone (UTC).

        Returns:
            DashboardMetrics with available data and error indicators for failures.
        """
        metrics = DashboardMetrics()

        # Calculate today's date boundaries (00:00:00 to 23:59:59 server timezone)
        today = date.today()
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today, time.max)

        # Fetch today's sales and transaction count
        await self._fetch_today_sales(metrics, today_start, today_end)

        # Fetch low-stock products
        await self._fetch_low_stock_products(metrics)

        # Fetch active staff count
        await self._fetch_active_staff_count(metrics)

        # Fetch recent transactions
        await self._fetch_recent_transactions(metrics)

        return metrics

    async def _fetch_today_sales(
        self,
        metrics: DashboardMetrics,
        today_start: datetime,
        today_end: datetime,
    ) -> None:
        """Fetch today's total sales and transaction count.

        Args:
            metrics: DashboardMetrics instance to populate.
            today_start: Start of the current day.
            today_end: End of the current day.
        """
        try:
            filters = TransactionFilters(
                date_from=today_start,
                date_to=today_end,
            )
            # Use a large page size to get all today's transactions for summing
            pagination = PaginationParams(page=1, page_size=100)
            result = await self._txn_repo.list(filters=filters, pagination=pagination)

            metrics.today_transaction_count = result.total_count

            # Sum up total amounts from the transactions we retrieved
            total_sales = Decimal("0.00")
            for transaction in result.items:
                total_sales += transaction.total_amount

            # If there are more transactions than we fetched, page through them
            if result.total_count > 100:
                total_pages = (result.total_count + 99) // 100
                for page_num in range(2, total_pages + 1):
                    page_pagination = PaginationParams(page=page_num, page_size=100)
                    page_result = await self._txn_repo.list(
                        filters=filters, pagination=page_pagination
                    )
                    for transaction in page_result.items:
                        total_sales += transaction.total_amount

            metrics.today_sales = total_sales
        except Exception as e:
            logger.error(f"Failed to fetch today's sales: {e}")
            metrics.errors["today_sales"] = "Failed to retrieve today's sales data"
            metrics.errors["today_transaction_count"] = (
                "Failed to retrieve today's transaction count"
            )

    async def _fetch_low_stock_products(self, metrics: DashboardMetrics) -> None:
        """Fetch products at or below the low-stock threshold.

        Args:
            metrics: DashboardMetrics instance to populate.
        """
        try:
            pagination = PaginationParams(page=1, page_size=100)
            result = await self._product_repo.get_low_stock(
                threshold=self._settings.LOW_STOCK_THRESHOLD,
                pagination=pagination,
            )
            metrics.low_stock_products = result.items
        except Exception as e:
            logger.error(f"Failed to fetch low-stock products: {e}")
            metrics.errors["low_stock_products"] = (
                "Failed to retrieve low-stock products"
            )

    async def _fetch_active_staff_count(self, metrics: DashboardMetrics) -> None:
        """Fetch the count of active staff users.

        Args:
            metrics: DashboardMetrics instance to populate.
        """
        try:
            filters = UserFilters(role=UserRole.staff, is_active=True)
            pagination = PaginationParams(page=1, page_size=1)
            result = await self._user_repo.list(filters=filters, pagination=pagination)
            metrics.active_staff_count = result.total_count
        except Exception as e:
            logger.error(f"Failed to fetch active staff count: {e}")
            metrics.errors["active_staff_count"] = (
                "Failed to retrieve active staff count"
            )

    async def _fetch_recent_transactions(self, metrics: DashboardMetrics) -> None:
        """Fetch the 10 most recent transactions with cashier names.

        Args:
            metrics: DashboardMetrics instance to populate.
        """
        try:
            filters = TransactionFilters()
            pagination = PaginationParams(page=1, page_size=10)
            result = await self._txn_repo.list(filters=filters, pagination=pagination)

            recent: list[RecentTransaction] = []
            for transaction in result.items:
                cashier_name = "Unknown"
                if (
                    hasattr(transaction, "cashier")
                    and transaction.cashier is not None
                ):
                    cashier_name = transaction.cashier.full_name

                recent.append(
                    RecentTransaction(
                        id=str(transaction.id),
                        total_amount=transaction.total_amount,
                        cashier_name=cashier_name,
                        created_at=transaction.created_at,
                    )
                )

            metrics.recent_transactions = recent
        except Exception as e:
            logger.error(f"Failed to fetch recent transactions: {e}")
            metrics.errors["recent_transactions"] = (
                "Failed to retrieve recent transactions"
            )

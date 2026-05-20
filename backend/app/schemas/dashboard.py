"""Dashboard Pydantic schemas for response validation.

Provides schemas for the admin dashboard endpoint:
- RecentTransactionResponse: Summary of a recent transaction
- DashboardMetrics: Internal dataclass-like schema for service layer
- DashboardResponse: Full dashboard response with all metrics
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.product import ProductResponse


class RecentTransactionResponse(BaseModel):
    """Schema for a recent transaction summary on the dashboard.

    Contains minimal transaction info for the dashboard overview.
    """

    id: uuid.UUID
    cashier_name: str
    total_amount: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardResponse(BaseModel):
    """Schema for the full dashboard metrics response.

    Includes today's sales, transaction count, low-stock products,
    active staff count, and recent transactions.
    """

    today_sales: Decimal = Field(description="Total sales amount for the current day")
    today_transaction_count: int = Field(
        description="Number of transactions for the current day"
    )
    low_stock_products: list[ProductResponse] = Field(
        default_factory=list,
        description="Products currently below the low-stock threshold",
    )
    active_staff_count: int = Field(
        description="Number of staff users with active accounts"
    )
    recent_transactions: list[RecentTransactionResponse] = Field(
        default_factory=list,
        description="10 most recent transactions with cashier name",
    )
    errors: Optional[dict[str, str]] = Field(
        default=None,
        description="Partial failure indicators keyed by metric name",
    )

    model_config = {"from_attributes": True}

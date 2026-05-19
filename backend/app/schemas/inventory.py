"""Inventory management Pydantic schemas for request/response validation.

Provides schemas for inventory operations:
- StockOperationRequest: Stock-in and stock-out request body
- StockAdjustmentRequest: Stock adjustment request body with mandatory reason
- InventoryLogResponse: Inventory log entry response data
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.enums import AdjustmentType


class StockOperationRequest(BaseModel):
    """Schema for stock-in and stock-out operations.

    Requires a product ID and a quantity within the allowed range (1 to 999,999).
    """

    product_id: uuid.UUID = Field(description="UUID of the product to adjust")
    quantity: int = Field(
        ge=1, le=999999, description="Quantity to add or remove (1 to 999,999)"
    )


class StockAdjustmentRequest(BaseModel):
    """Schema for stock adjustment operations.

    Sets the product stock to an exact quantity with a mandatory reason.
    """

    product_id: uuid.UUID = Field(description="UUID of the product to adjust")
    new_quantity: int = Field(
        ge=0, le=999999, description="Target stock quantity (0 to 999,999)"
    )
    reason: str = Field(
        min_length=1,
        max_length=500,
        description="Mandatory reason for the adjustment (1 to 500 characters)",
    )


class InventoryLogResponse(BaseModel):
    """Schema for inventory log entry in API responses.

    Includes adjustment type, quantity change, performing user, reason, and timestamp.
    """

    id: uuid.UUID
    product_id: uuid.UUID
    user_id: uuid.UUID
    adjustment_type: AdjustmentType
    quantity_change: int
    reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

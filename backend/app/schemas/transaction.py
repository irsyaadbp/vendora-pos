"""Transaction Pydantic schemas for request/response validation.

Provides schemas for POS transaction operations:
- TransactionItemCreate: Single line item in a transaction request
- TransactionCreate: Full transaction creation request
- ReceiptItemResponse: Single line item in a receipt response
- TransactionReceiptResponse: Complete receipt returned after transaction creation
- TransactionItemResponse: Transaction item in list/detail responses
- TransactionResponse: Transaction data in list/detail responses
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.enums import DiscountType, PaymentMethod, TransactionStatus


class TransactionItemCreate(BaseModel):
    """Schema for a single line item in a transaction creation request.

    Each item specifies a product and the quantity to purchase.
    """

    product_id: uuid.UUID = Field(description="UUID of the product to purchase")
    quantity: int = Field(ge=1, description="Quantity to purchase (minimum 1)")


class TransactionCreate(BaseModel):
    """Schema for creating a new transaction.

    Contains the cart items, optional discount, and payment method.
    """

    items: list[TransactionItemCreate] = Field(
        min_length=1, max_length=100, description="List of items to purchase (1-100 items)"
    )
    discount_type: Optional[DiscountType] = Field(
        None, description="Discount type: percentage or fixed"
    )
    discount_value: Optional[Decimal] = Field(
        None, ge=Decimal("0"), description="Discount value (percentage 0-100 or fixed amount)"
    )
    payment_method: PaymentMethod = Field(description="Payment method for the transaction")


class ReceiptItemResponse(BaseModel):
    """Schema for a single line item in a transaction receipt."""

    product_id: uuid.UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class TransactionReceiptResponse(BaseModel):
    """Schema for the complete receipt returned after successful transaction creation."""

    id: uuid.UUID
    items: list[ReceiptItemResponse]
    total_amount: Decimal
    discount_amount: Decimal
    payment_method: PaymentMethod
    cashier_name: str
    created_at: datetime


class TransactionItemResponse(BaseModel):
    """Schema for a transaction item in list/detail responses."""

    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = {"from_attributes": True}


class TransactionResponse(BaseModel):
    """Schema for transaction data in API responses."""

    id: uuid.UUID
    cashier_id: uuid.UUID
    total_amount: Decimal
    discount_amount: Decimal
    payment_method: PaymentMethod
    status: TransactionStatus
    created_at: datetime
    items: list[TransactionItemResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}

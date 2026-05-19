"""Product management Pydantic schemas for request/response validation.

Provides schemas for product CRUD operations:
- ProductCreate: New product creation request
- ProductUpdate: Partial product update request
- ProductResponse: Product data response with computed low_stock field
- ProductFilters: Query parameters for product search/filtering
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """Schema for creating a new product.

    All required fields must be provided. SKU must be unique.
    Barcode is optional but must be unique if provided.
    """

    name: str = Field(min_length=1, max_length=255, description="Product name")
    sku: str = Field(min_length=1, max_length=100, description="Stock Keeping Unit (must be unique)")
    barcode: Optional[str] = Field(None, max_length=100, description="Product barcode (must be unique if provided)")
    price: Decimal = Field(ge=Decimal("0.01"), le=Decimal("999999999.99"), description="Product price")
    stock: int = Field(ge=0, description="Initial stock quantity")
    category_id: Optional[uuid.UUID] = Field(None, description="Category UUID")


class ProductUpdate(BaseModel):
    """Schema for updating an existing product.

    All fields are optional. Only provided fields will be updated.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Product name")
    sku: Optional[str] = Field(None, min_length=1, max_length=100, description="Stock Keeping Unit")
    barcode: Optional[str] = Field(None, max_length=100, description="Product barcode")
    price: Optional[Decimal] = Field(None, ge=Decimal("0.01"), le=Decimal("999999999.99"), description="Product price")
    stock: Optional[int] = Field(None, ge=0, description="Stock quantity")
    category_id: Optional[uuid.UUID] = Field(None, description="Category UUID")
    is_active: Optional[bool] = Field(None, description="Product active status")


class ProductResponse(BaseModel):
    """Schema for product data in API responses.

    Includes a computed low_stock field based on the configured threshold.
    """

    id: uuid.UUID
    name: str
    sku: str
    barcode: Optional[str]
    price: Decimal
    stock: int
    category_id: Optional[uuid.UUID]
    is_active: bool
    low_stock: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductFilters(BaseModel):
    """Query parameters for filtering product search results."""

    category_id: Optional[uuid.UUID] = Field(None, description="Filter by category ID")
    is_active: Optional[bool] = Field(None, description="Filter by active status")

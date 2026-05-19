"""Category management Pydantic schemas for request/response validation.

Provides schemas for category CRUD operations:
- CategoryCreate: New category creation request
- CategoryUpdate: Partial category update request
- CategoryResponse: Category data response
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    """Schema for creating a new category.

    Name is required and must be unique.
    """

    name: str = Field(min_length=1, max_length=100, description="Category name (must be unique)")
    description: Optional[str] = Field(None, max_length=500, description="Category description")


class CategoryUpdate(BaseModel):
    """Schema for updating an existing category.

    All fields are optional. Only provided fields will be updated.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, max_length=500, description="Category description")


class CategoryResponse(BaseModel):
    """Schema for category data in API responses."""

    id: uuid.UUID
    name: str
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

"""User management Pydantic schemas for request/response validation.

Provides schemas for user CRUD operations:
- UserCreate: New user creation request
- UserUpdate: Partial user update request
- UserResponse: User data response (excludes password_hash)
- PasswordReset: Password reset request
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.enums import UserRole


class UserCreate(BaseModel):
    """Schema for creating a new user.

    All fields are required. Password will be hashed before storage.
    """

    full_name: str = Field(min_length=1, max_length=100, description="User's full name")
    email: EmailStr = Field(description="User's email address (must be unique)")
    password: str = Field(min_length=8, description="Password (minimum 8 characters)")
    role: UserRole = Field(description="User role (admin or staff)")


class UserUpdate(BaseModel):
    """Schema for updating an existing user.

    All fields are optional. Only provided fields will be updated.
    """

    full_name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="User's full name"
    )
    email: Optional[EmailStr] = Field(None, description="User's email address")
    role: Optional[UserRole] = Field(None, description="User role (admin or staff)")
    is_active: Optional[bool] = Field(None, description="Account active status")


class UserResponse(BaseModel):
    """Schema for user data in API responses.

    Excludes sensitive fields like password_hash.
    """

    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PasswordReset(BaseModel):
    """Schema for resetting a user's password."""

    new_password: str = Field(min_length=8, description="New password (minimum 8 characters)")

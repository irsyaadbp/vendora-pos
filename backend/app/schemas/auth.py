"""Authentication request and response schemas.

Defines Pydantic models for login requests and token responses
used by the auth API endpoints.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.enums import UserRole


class LoginRequest(BaseModel):
    """Schema for user login request."""

    email: EmailStr
    password: str = Field(min_length=8)


class UserInfo(BaseModel):
    """Minimal user info returned with login response."""

    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    """Schema for login response with access token and user info.

    refresh_token is included so the Next.js proxy can set it as an
    httpOnly cookie. Node.js fetch() strips Set-Cookie headers in
    server-to-server calls, so the proxy must read it from the body.
    The proxy MUST NOT forward refresh_token to the browser.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserInfo


class TokenResponse(BaseModel):
    """Schema for token refresh response.

    refresh_token is included so the Next.js proxy can rotate the
    httpOnly cookie. The proxy MUST NOT forward it to the browser.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"

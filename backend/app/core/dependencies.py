"""FastAPI dependencies for request parameter extraction and validation.

Provides reusable dependencies for pagination, authentication, and authorization
that can be injected into route handlers.
"""

import uuid
from dataclasses import dataclass

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.infrastructure.security import verify_access_token
from app.models.user import User
from app.schemas.enums import UserRole

# OAuth2 scheme extracts the Bearer token from the Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass
class PaginationParams:
    """Pagination parameters extracted from query string.

    Attributes:
        page: Current page number (1-indexed, minimum 1).
        page_size: Number of items per page (minimum 1, maximum 100).
    """

    page: int
    page_size: int

    @property
    def offset(self) -> int:
        """Compute the database offset for the current page."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Compute the database limit (same as page_size)."""
        return self.page_size


async def get_pagination(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(
        default=20, ge=1, le=100, description="Number of items per page (max 100)"
    ),
) -> PaginationParams:
    """Dependency that extracts and validates pagination parameters from query string.

    Args:
        page: Page number, defaults to 1, must be >= 1.
        page_size: Items per page, defaults to 20, must be between 1 and 100.

    Returns:
        PaginationParams instance with computed offset and limit.
    """
    return PaginationParams(page=page, page_size=page_size)


async def _get_db_session():  # type: ignore[no-untyped-def]
    """Lazy wrapper for get_db_session to avoid circular imports at module level."""
    from app.infrastructure.database import get_db_session

    async for session in get_db_session():
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(_get_db_session),
) -> User:
    """Dependency that extracts and verifies the current authenticated user.

    Extracts the JWT from the Authorization header, verifies its signature
    and expiration, looks up the user by the token's "sub" claim, and
    checks that the user account is active.

    Args:
        token: JWT access token extracted from Authorization header.
        session: Async database session for user lookup.

    Returns:
        The authenticated User instance.

    Raises:
        UnauthorizedException: If the token is missing, invalid, expired,
            the user does not exist, or the user account is inactive.
    """
    # Verify the JWT token (signature, expiration, structure)
    try:
        payload = verify_access_token(token)
    except ValueError:
        raise UnauthorizedException(message="Invalid or expired token")

    # Extract user ID from the "sub" claim
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException(message="Invalid token: missing subject")

    try:
        user_id = uuid.UUID(user_id_str)
    except (ValueError, TypeError):
        raise UnauthorizedException(message="Invalid token: malformed subject")

    # Look up the user in the database (local import to avoid circular dependency)
    from app.repositories.user_repository import UserRepository

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if user is None:
        raise UnauthorizedException(message="User not found")

    # Check that the user account is active
    if not user.is_active:
        raise UnauthorizedException(message="User account is inactive")

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency that requires the current user to have the admin role.

    Wraps get_current_user and additionally checks that the authenticated
    user has the admin role.

    Args:
        current_user: The authenticated user from get_current_user.

    Returns:
        The authenticated admin User instance.

    Raises:
        ForbiddenException: If the user's role is not admin.
    """
    if current_user.role != UserRole.admin:
        raise ForbiddenException(message="Admin access required")

    return current_user

"""User management API routes.

All endpoints require admin role. Provides CRUD operations for user
accounts including creation, listing, updating, password reset, and
deactivation.
"""

import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import PaginationParams, get_pagination, require_admin
from app.domain.interfaces import UserFilters
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.common import APIResponse, PaginatedMeta, PaginatedResponse
from app.schemas.enums import UserRole
from app.schemas.user import PasswordReset, UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


async def _get_db_session():  # type: ignore[no-untyped-def]
    """Lazy wrapper for get_db_session to avoid circular imports at module level."""
    from app.infrastructure.database import get_db_session

    async for session in get_db_session():
        yield session


def _get_user_service(session: AsyncSession) -> UserService:
    """Construct a UserService with required repository dependency.

    Args:
        session: The async database session for the current request.

    Returns:
        A fully-initialized UserService instance.
    """
    user_repo = UserRepository(session)
    return UserService(user_repo=user_repo)


def _to_user_response(user: User) -> UserResponse:
    """Convert a User model instance to a UserResponse schema.

    Args:
        user: The SQLAlchemy User model instance.

    Returns:
        UserResponse schema excluding password_hash.
    """
    return UserResponse.model_validate(user)


@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    pagination: PaginationParams = Depends(get_pagination),
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> PaginatedResponse[UserResponse]:
    """List users with search, filtering, and pagination.

    Requires admin role. Supports search by name/email, filter by role,
    and filter by active status. Results are sorted by created_at descending.
    """
    user_service = _get_user_service(session)
    filters = UserFilters(search=search, role=role, is_active=is_active)
    result = await user_service.list_users(filters=filters, pagination=pagination)

    user_responses = [_to_user_response(user) for user in result.items]
    total_pages = math.ceil(result.total_count / pagination.page_size) if result.total_count > 0 else 0

    return PaginatedResponse(
        success=True,
        data=user_responses,
        message="Users retrieved successfully",
        meta=PaginatedMeta(
            total_count=result.total_count,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        ),
    )


@router.post("/", response_model=APIResponse[UserResponse], status_code=201)
async def create_user(
    body: UserCreate,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[UserResponse]:
    """Create a new user account.

    Requires admin role. Validates email uniqueness and hashes the password
    before storage. Returns the created user without password_hash.
    """
    user_service = _get_user_service(session)
    user = await user_service.create_user(
        full_name=body.full_name,
        email=body.email,
        password=body.password,
        role=body.role,
    )
    await session.commit()

    return APIResponse(
        success=True,
        data=_to_user_response(user),
        message="User created successfully",
    )


@router.get("/{user_id}", response_model=APIResponse[UserResponse])
async def get_user(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[UserResponse]:
    """Get a single user by ID.

    Requires admin role. Returns 404 if user does not exist.
    """
    from app.core.exceptions import NotFoundException

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)

    if user is None:
        raise NotFoundException(message="User not found")

    return APIResponse(
        success=True,
        data=_to_user_response(user),
        message="User retrieved successfully",
    )


@router.put("/{user_id}", response_model=APIResponse[UserResponse])
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[UserResponse]:
    """Update an existing user's fields.

    Requires admin role. Only provided fields will be updated.
    Returns 404 if user does not exist, 409 for duplicate email.
    """
    user_service = _get_user_service(session)
    user = await user_service.update_user(
        user_id=user_id,
        full_name=body.full_name,
        email=body.email,
        role=body.role,
        is_active=body.is_active,
    )
    await session.commit()

    return APIResponse(
        success=True,
        data=_to_user_response(user),
        message="User updated successfully",
    )


@router.post("/{user_id}/reset-password", response_model=APIResponse[None])
async def reset_password(
    user_id: uuid.UUID,
    body: PasswordReset,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[None]:
    """Reset a user's password.

    Requires admin role. Hashes the new password before storage.
    Returns 404 if user does not exist.
    """
    user_service = _get_user_service(session)
    await user_service.reset_password(user_id=user_id, new_password=body.new_password)
    await session.commit()

    return APIResponse(
        success=True,
        data=None,
        message="Password reset successfully",
    )


@router.patch("/{user_id}/deactivate", response_model=APIResponse[UserResponse])
async def deactivate_user(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[UserResponse]:
    """Deactivate a user account.

    Requires admin role. Sets is_active to false.
    Returns 404 if user does not exist.
    """
    user_service = _get_user_service(session)
    user = await user_service.deactivate_user(user_id=user_id)
    await session.commit()

    return APIResponse(
        success=True,
        data=_to_user_response(user),
        message="User deactivated successfully",
    )

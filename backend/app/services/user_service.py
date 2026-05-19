"""User management service handling CRUD operations.

Provides user creation with email uniqueness validation and password hashing,
user updates with field restriction, password reset, deactivation, and
paginated listing with search and filters.
"""

import uuid

from app.core.dependencies import PaginationParams
from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.domain.interfaces import (
    PaginatedResult,
    UserFilters,
    UserRepositoryInterface,
)
from app.infrastructure.security import hash_password
from app.models.user import User
from app.schemas.common import FieldError
from app.schemas.enums import UserRole


class UserService:
    """Service for user management operations.

    Handles user creation, updates, password resets, deactivation,
    and paginated listing with search and filtering capabilities.
    All operations enforce business rules including email uniqueness
    and password complexity requirements.
    """

    def __init__(self, user_repo: UserRepositoryInterface) -> None:
        """Initialize UserService with required repository dependency.

        Args:
            user_repo: Repository for user data access operations.
        """
        self._user_repo = user_repo

    async def create_user(
        self,
        full_name: str,
        email: str,
        password: str,
        role: UserRole,
    ) -> User:
        """Create a new user with validated unique email and hashed password.

        Args:
            full_name: User's full name (1-100 characters).
            email: User's email address (must be unique).
            password: Plaintext password (minimum 8 characters).
            role: User role (admin or staff).

        Returns:
            The created User instance.

        Raises:
            ValidationException: If input validation fails (password too short,
                full_name empty or too long).
            ConflictException: If the email is already in use.
        """
        # Validate full_name
        errors: list[FieldError] = []
        if not full_name or not full_name.strip():
            errors.append(
                FieldError(field="full_name", detail="Full name is required")
            )
        elif len(full_name) > 100:
            errors.append(
                FieldError(
                    field="full_name",
                    detail="Full name must be at most 100 characters",
                )
            )

        # Validate password length
        if len(password) < 8:
            errors.append(
                FieldError(
                    field="password",
                    detail="Password must be at least 8 characters",
                )
            )

        if errors:
            raise ValidationException(message="Validation failed", errors=errors)

        # Check email uniqueness
        existing_user = await self._user_repo.get_by_email(email)
        if existing_user is not None:
            raise ConflictException(message="A user with this email already exists")

        # Hash password and create user
        password_hash = hash_password(password)
        user = await self._user_repo.create(
            full_name=full_name.strip(),
            email=email,
            password_hash=password_hash,
            role=role,
        )

        return user

    async def update_user(
        self,
        user_id: uuid.UUID,
        full_name: str | None = None,
        email: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
    ) -> User:
        """Update allowed fields for an existing user.

        Only full_name, email, role, and is_active can be updated.
        Validates email uniqueness if email is being changed.

        Args:
            user_id: The UUID of the user to update.
            full_name: New full name (optional, 1-100 characters).
            email: New email address (optional, must be unique).
            role: New role (optional).
            is_active: New active status (optional).

        Returns:
            The updated User instance.

        Raises:
            NotFoundException: If the user does not exist.
            ValidationException: If input validation fails.
            ConflictException: If the new email is already in use.
        """
        # Check user exists
        existing_user = await self._user_repo.get_by_id(user_id)
        if existing_user is None:
            raise NotFoundException(message="User not found")

        # Validate fields
        errors: list[FieldError] = []
        if full_name is not None:
            if not full_name.strip():
                errors.append(
                    FieldError(field="full_name", detail="Full name is required")
                )
            elif len(full_name) > 100:
                errors.append(
                    FieldError(
                        field="full_name",
                        detail="Full name must be at most 100 characters",
                    )
                )

        if errors:
            raise ValidationException(message="Validation failed", errors=errors)

        # Check email uniqueness if email is being changed
        if email is not None and email != existing_user.email:
            email_user = await self._user_repo.get_by_email(email)
            if email_user is not None:
                raise ConflictException(
                    message="A user with this email already exists"
                )

        # Build update kwargs with only provided fields
        update_kwargs: dict[str, object] = {}
        if full_name is not None:
            update_kwargs["full_name"] = full_name.strip()
        if email is not None:
            update_kwargs["email"] = email
        if role is not None:
            update_kwargs["role"] = role
        if is_active is not None:
            update_kwargs["is_active"] = is_active

        if not update_kwargs:
            # Nothing to update, return existing user
            return existing_user

        updated_user = await self._user_repo.update(user_id, **update_kwargs)
        if updated_user is None:
            raise NotFoundException(message="User not found")

        return updated_user

    async def reset_password(
        self,
        user_id: uuid.UUID,
        new_password: str,
    ) -> None:
        """Reset a user's password with a new hashed password.

        Args:
            user_id: The UUID of the user whose password to reset.
            new_password: The new plaintext password (minimum 8 characters).

        Raises:
            NotFoundException: If the user does not exist.
            ValidationException: If the new password is too short.
        """
        # Validate password length
        if len(new_password) < 8:
            raise ValidationException(
                message="Validation failed",
                errors=[
                    FieldError(
                        field="password",
                        detail="Password must be at least 8 characters",
                    )
                ],
            )

        # Check user exists
        existing_user = await self._user_repo.get_by_id(user_id)
        if existing_user is None:
            raise NotFoundException(message="User not found")

        # Hash and update password
        password_hash = hash_password(new_password)
        await self._user_repo.update(user_id, password_hash=password_hash)

    async def deactivate_user(self, user_id: uuid.UUID) -> User:
        """Deactivate a user account by setting is_active to false.

        Args:
            user_id: The UUID of the user to deactivate.

        Returns:
            The updated User instance with is_active set to false.

        Raises:
            NotFoundException: If the user does not exist.
        """
        existing_user = await self._user_repo.get_by_id(user_id)
        if existing_user is None:
            raise NotFoundException(message="User not found")

        updated_user = await self._user_repo.update(user_id, is_active=False)
        if updated_user is None:
            raise NotFoundException(message="User not found")

        return updated_user

    async def list_users(
        self,
        filters: UserFilters,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """List users with filtering and pagination.

        Returns paginated results sorted by created_at descending.
        Supports search by name/email, filter by role, and filter by
        active status.

        Args:
            filters: Filtering criteria (search, role, is_active).
            pagination: Pagination parameters (page, page_size).

        Returns:
            PaginatedResult containing matching users and total count.
        """
        return await self._user_repo.list(filters=filters, pagination=pagination)

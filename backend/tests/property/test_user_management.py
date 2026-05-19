"""Property-based tests for user management.

Feature: vendora-pos-foundation
Property 11: User creation returns record without password hash
Property 12: Email uniqueness constraint
Property 13: User update applies only allowed fields
Property 14: Paginated list respects filters and bounds
Property 15: Input validation returns field-specific errors

Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.7, 5.11

These tests verify UserService behavior and UserResponse schema
using property-based testing with Hypothesis strategies.
"""

import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

# Set environment variables before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-property-tests-minimum-length")

from app.core.dependencies import PaginationParams
from app.core.exceptions import ConflictException, ValidationException
from app.domain.interfaces import PaginatedResult, UserFilters
from app.models.user import User
from app.schemas.enums import UserRole
from app.schemas.user import UserResponse
from app.services.user_service import UserService


# --- Strategies ---

full_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Zs"),
        blacklist_characters="\x00\n\r\t",
    ),
    min_size=1,
    max_size=100,
).filter(lambda s: len(s.strip()) > 0)

email_local_strategy = st.from_regex(r"[a-z][a-z0-9]{2,15}", fullmatch=True)
email_domain_strategy = st.from_regex(r"[a-z]{3,10}\.(com|org|net)", fullmatch=True)
email_strategy = st.builds(
    lambda local, domain: f"{local}@{domain}",
    email_local_strategy,
    email_domain_strategy,
)

password_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters="\x00",
        max_codepoint=127,
    ),
    min_size=8,
    max_size=72,
)

role_strategy = st.sampled_from([UserRole.admin, UserRole.staff])

user_id_strategy = st.uuids()

page_strategy = st.integers(min_value=1, max_value=100)
page_size_strategy = st.integers(min_value=1, max_value=100)


# --- Helpers ---


def _make_mock_user(
    user_id: uuid.UUID | None = None,
    full_name: str = "Test User",
    email: str = "test@example.com",
    password_hash: str = "$2b$12$fakehashvalue",
    role: UserRole = UserRole.staff,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock User object with all required attributes."""
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.full_name = full_name
    user.email = email
    user.password_hash = password_hash
    user.role = role
    user.is_active = is_active
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


# --- Property 11: User creation returns record without password hash ---


class TestUserCreationNoPasswordHash:
    """**Validates: Requirements 5.1**

    Property 11: User creation returns record without password hash.
    For any valid user creation request, the UserResponse schema SHALL
    exclude the password_hash field from the response.
    """

    @given(
        full_name=full_name_strategy,
        email=email_strategy,
        password=password_strategy,
        role=role_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_user_response_schema_excludes_password_hash(
        self, full_name: str, email: str, password: str, role: UserRole
    ):
        """For any valid user data, UserResponse never contains password_hash."""
        user_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # Create a mock user object that has password_hash (as the model does)
        mock_user = _make_mock_user(
            user_id=user_id,
            full_name=full_name.strip(),
            email=email,
            password_hash="$2b$12$somehashvalue",
            role=role,
            is_active=True,
        )
        mock_user.created_at = now
        mock_user.updated_at = now

        # Serialize through UserResponse schema
        response = UserResponse.model_validate(mock_user, from_attributes=True)
        response_dict = response.model_dump()

        # password_hash must NOT be in the response
        assert "password_hash" not in response_dict, (
            "UserResponse must never contain password_hash"
        )
        # Verify expected fields ARE present
        assert "id" in response_dict
        assert "full_name" in response_dict
        assert "email" in response_dict
        assert "role" in response_dict
        assert "is_active" in response_dict
        assert "created_at" in response_dict
        assert "updated_at" in response_dict

    @given(
        full_name=full_name_strategy,
        email=email_strategy,
        password=password_strategy,
        role=role_strategy,
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_create_user_service_returns_user_without_exposing_hash_in_schema(
        self, full_name: str, email: str, password: str, role: UserRole
    ):
        """For any valid creation, the service returns a User that when serialized
        through UserResponse excludes password_hash."""
        user_repo = AsyncMock()
        user_repo.get_by_email.return_value = None

        created_user = _make_mock_user(
            full_name=full_name.strip(),
            email=email,
            password_hash="$2b$12$hashed",
            role=role,
        )
        user_repo.create.return_value = created_user

        service = UserService(user_repo=user_repo)

        with patch("app.services.user_service.hash_password", return_value="$2b$12$hashed"):
            result = await service.create_user(
                full_name=full_name,
                email=email,
                password=password,
                role=role,
            )

        # The result is a User model — when serialized via UserResponse, no password_hash
        response = UserResponse.model_validate(result, from_attributes=True)
        response_dict = response.model_dump()
        assert "password_hash" not in response_dict
        assert "password" not in response_dict


# --- Property 12: Email uniqueness constraint ---


class TestEmailUniquenessConstraint:
    """**Validates: Requirements 5.2, 5.3**

    Property 12: Email uniqueness constraint.
    For any email that already exists, create_user SHALL raise
    ConflictException.
    """

    @given(
        full_name=full_name_strategy,
        email=email_strategy,
        password=password_strategy,
        role=role_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_duplicate_email_raises_conflict(
        self, full_name: str, email: str, password: str, role: UserRole
    ):
        """For any email that already exists, create_user raises ConflictException."""
        user_repo = AsyncMock()
        # Simulate existing user with same email
        existing_user = _make_mock_user(email=email)
        user_repo.get_by_email.return_value = existing_user

        service = UserService(user_repo=user_repo)

        with pytest.raises(ConflictException) as exc_info:
            await service.create_user(
                full_name=full_name,
                email=email,
                password=password,
                role=role,
            )

        assert "email already exists" in exc_info.value.message.lower()

    @given(
        user_id=user_id_strategy,
        existing_email=email_strategy,
        new_email=email_strategy,
        role=role_strategy,
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_update_to_existing_email_raises_conflict(
        self,
        user_id: uuid.UUID,
        existing_email: str,
        new_email: str,
        role: UserRole,
    ):
        """For any update changing email to one that exists, raises ConflictException."""
        assume(existing_email != new_email)

        user_repo = AsyncMock()
        # Current user has existing_email
        current_user = _make_mock_user(user_id=user_id, email=existing_email)
        user_repo.get_by_id.return_value = current_user
        # Another user already has new_email
        other_user = _make_mock_user(email=new_email)
        user_repo.get_by_email.return_value = other_user

        service = UserService(user_repo=user_repo)

        with pytest.raises(ConflictException) as exc_info:
            await service.update_user(user_id, email=new_email)

        assert "email already exists" in exc_info.value.message.lower()


# --- Property 13: User update applies only allowed fields ---


class TestUserUpdateAllowedFields:
    """**Validates: Requirements 5.4**

    Property 13: User update applies only allowed fields.
    Only full_name, email, role, is_active can be updated via update_user.
    The service method signature enforces this — it only accepts these fields.
    """

    @given(
        user_id=user_id_strategy,
        new_full_name=st.one_of(st.none(), full_name_strategy),
        new_email=st.one_of(st.none(), email_strategy),
        new_role=st.one_of(st.none(), role_strategy),
        new_is_active=st.one_of(st.none(), st.booleans()),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_update_only_passes_allowed_fields_to_repo(
        self,
        user_id: uuid.UUID,
        new_full_name: str | None,
        new_email: str | None,
        new_role: UserRole | None,
        new_is_active: bool | None,
    ):
        """For any combination of allowed update fields, only provided fields
        are passed to the repository update method."""
        # Skip if all fields are None (nothing to update)
        assume(
            new_full_name is not None
            or new_email is not None
            or new_role is not None
            or new_is_active is not None
        )

        user_repo = AsyncMock()
        existing_user = _make_mock_user(user_id=user_id, email="original@example.com")
        user_repo.get_by_id.return_value = existing_user
        # If email is changing, no conflict
        user_repo.get_by_email.return_value = None
        updated_user = _make_mock_user(user_id=user_id)
        user_repo.update.return_value = updated_user

        service = UserService(user_repo=user_repo)

        await service.update_user(
            user_id,
            full_name=new_full_name,
            email=new_email,
            role=new_role,
            is_active=new_is_active,
        )

        # Verify only provided (non-None) fields were passed to repo.update
        call_args = user_repo.update.call_args
        update_kwargs = call_args[1] if call_args[1] else {}
        # Remove user_id positional arg
        passed_user_id = call_args[0][0] if call_args[0] else None
        assert passed_user_id == user_id

        allowed_fields = {"full_name", "email", "role", "is_active"}
        # All keys in update_kwargs must be in allowed_fields
        for key in update_kwargs:
            assert key in allowed_fields, (
                f"Disallowed field '{key}' was passed to repository update"
            )

        # Verify each provided field is present
        if new_full_name is not None:
            assert "full_name" in update_kwargs
            assert update_kwargs["full_name"] == new_full_name.strip()
        if new_email is not None:
            assert "email" in update_kwargs
        if new_role is not None:
            assert "role" in update_kwargs
            assert update_kwargs["role"] == new_role
        if new_is_active is not None:
            assert "is_active" in update_kwargs
            assert update_kwargs["is_active"] == new_is_active

    @given(user_id=user_id_strategy)
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_update_user_does_not_accept_password_hash(
        self, user_id: uuid.UUID
    ):
        """The update_user method signature does not accept password_hash directly.
        This ensures password_hash cannot be set through the update endpoint."""
        user_repo = AsyncMock()
        existing_user = _make_mock_user(user_id=user_id)
        user_repo.get_by_id.return_value = existing_user
        user_repo.update.return_value = existing_user

        service = UserService(user_repo=user_repo)

        # Verify that update_user does not accept password_hash as a parameter
        import inspect

        sig = inspect.signature(service.update_user)
        param_names = set(sig.parameters.keys())

        # password_hash should NOT be an accepted parameter
        assert "password_hash" not in param_names, (
            "update_user must not accept password_hash as a parameter"
        )
        assert "password" not in param_names, (
            "update_user must not accept password as a parameter"
        )


# --- Property 14: Paginated list respects filters and bounds ---


class TestPaginatedListRespectsFiltersAndBounds:
    """**Validates: Requirements 5.7**

    Property 14: Paginated list respects filters and bounds.
    For any page/page_size within bounds, list_users returns correct
    pagination metadata and respects the page_size limit.
    """

    @given(
        page=page_strategy,
        page_size=page_size_strategy,
        total_count=st.integers(min_value=0, max_value=500),
        role_filter=st.one_of(st.none(), role_strategy),
        is_active_filter=st.one_of(st.none(), st.booleans()),
        search_filter=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_list_users_respects_pagination_bounds(
        self,
        page: int,
        page_size: int,
        total_count: int,
        role_filter: UserRole | None,
        is_active_filter: bool | None,
        search_filter: str | None,
    ):
        """For any valid pagination params, the returned items count does not
        exceed page_size and filters are passed correctly."""
        # Calculate how many items should be on this page
        items_on_page = min(page_size, max(0, total_count - (page - 1) * page_size))
        items_on_page = max(0, items_on_page)

        mock_users = [_make_mock_user() for _ in range(items_on_page)]
        paginated_result = PaginatedResult(items=mock_users, total_count=total_count)

        user_repo = AsyncMock()
        user_repo.list.return_value = paginated_result

        service = UserService(user_repo=user_repo)

        filters = UserFilters(
            search=search_filter,
            role=role_filter,
            is_active=is_active_filter,
        )
        pagination = PaginationParams(page=page, page_size=page_size)

        result = await service.list_users(filters=filters, pagination=pagination)

        # Result count must not exceed page_size
        assert len(result.items) <= page_size, (
            f"Returned {len(result.items)} items but page_size is {page_size}"
        )

        # Total count must be non-negative
        assert result.total_count >= 0

        # Verify filters were passed to repository
        call_kwargs = user_repo.list.call_args[1]
        assert call_kwargs["filters"].search == search_filter
        assert call_kwargs["filters"].role == role_filter
        assert call_kwargs["filters"].is_active == is_active_filter
        assert call_kwargs["pagination"].page == page
        assert call_kwargs["pagination"].page_size == page_size

    @given(
        page=page_strategy,
        page_size=page_size_strategy,
        total_count=st.integers(min_value=0, max_value=500),
    )
    @settings(max_examples=100, deadline=None)
    def test_pagination_params_offset_calculation(
        self, page: int, page_size: int, total_count: int
    ):
        """For any page/page_size, offset = (page - 1) * page_size."""
        pagination = PaginationParams(page=page, page_size=page_size)

        expected_offset = (page - 1) * page_size
        assert pagination.offset == expected_offset, (
            f"Offset {pagination.offset} != expected {expected_offset}"
        )
        assert pagination.limit == page_size, (
            f"Limit {pagination.limit} != page_size {page_size}"
        )


# --- Property 15: Input validation returns field-specific errors ---


class TestInputValidationFieldSpecificErrors:
    """**Validates: Requirements 5.11**

    Property 15: Input validation returns field-specific errors.
    For any invalid input, validation errors include the specific field name.
    """

    @given(
        short_password=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N"), max_codepoint=127),
            min_size=1,
            max_size=7,
        ),
        email=email_strategy,
        role=role_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_short_password_error_includes_field_name(
        self, short_password: str, email: str, role: UserRole
    ):
        """For any password shorter than 8 chars, error includes 'password' field."""
        user_repo = AsyncMock()
        service = UserService(user_repo=user_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_user(
                full_name="Valid Name",
                email=email,
                password=short_password,
                role=role,
            )

        error_fields = [e.field for e in exc_info.value.errors]
        assert "password" in error_fields, (
            f"Expected 'password' in error fields, got {error_fields}"
        )

    @given(
        email=email_strategy,
        password=password_strategy,
        role=role_strategy,
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_empty_name_error_includes_field_name(
        self, email: str, password: str, role: UserRole
    ):
        """For any empty full_name, error includes 'full_name' field."""
        user_repo = AsyncMock()
        service = UserService(user_repo=user_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_user(
                full_name="",
                email=email,
                password=password,
                role=role,
            )

        error_fields = [e.field for e in exc_info.value.errors]
        assert "full_name" in error_fields, (
            f"Expected 'full_name' in error fields, got {error_fields}"
        )

    @given(
        long_name=st.text(
            alphabet=st.characters(whitelist_categories=("L",), max_codepoint=127),
            min_size=101,
            max_size=200,
        ),
        email=email_strategy,
        password=password_strategy,
        role=role_strategy,
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_long_name_error_includes_field_name(
        self, long_name: str, email: str, password: str, role: UserRole
    ):
        """For any full_name > 100 chars, error includes 'full_name' field."""
        user_repo = AsyncMock()
        service = UserService(user_repo=user_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_user(
                full_name=long_name,
                email=email,
                password=password,
                role=role,
            )

        error_fields = [e.field for e in exc_info.value.errors]
        assert "full_name" in error_fields, (
            f"Expected 'full_name' in error fields, got {error_fields}"
        )

    @given(
        short_password=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N"), max_codepoint=127),
            min_size=1,
            max_size=7,
        ),
        email=email_strategy,
        role=role_strategy,
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_multiple_validation_errors_include_all_field_names(
        self, short_password: str, email: str, role: UserRole
    ):
        """For multiple invalid fields, all field names are included in errors."""
        user_repo = AsyncMock()
        service = UserService(user_repo=user_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_user(
                full_name="",  # Invalid: empty
                email=email,
                password=short_password,  # Invalid: too short
                role=role,
            )

        error_fields = [e.field for e in exc_info.value.errors]
        assert "full_name" in error_fields, (
            f"Expected 'full_name' in error fields, got {error_fields}"
        )
        assert "password" in error_fields, (
            f"Expected 'password' in error fields, got {error_fields}"
        )

    @given(
        email=email_strategy,
        password=password_strategy,
        role=role_strategy,
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_whitespace_only_name_error_includes_field_name(
        self, email: str, password: str, role: UserRole
    ):
        """For any whitespace-only full_name, error includes 'full_name' field."""
        user_repo = AsyncMock()
        service = UserService(user_repo=user_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_user(
                full_name="   ",
                email=email,
                password=password,
                role=role,
            )

        error_fields = [e.field for e in exc_info.value.errors]
        assert "full_name" in error_fields, (
            f"Expected 'full_name' in error fields, got {error_fields}"
        )

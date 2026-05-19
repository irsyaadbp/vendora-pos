"""Unit tests for UserService."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
from app.schemas.enums import UserRole
from app.services.user_service import UserService


# --- Helpers ---


def _make_user(
    user_id: Optional[uuid.UUID] = None,
    full_name: str = "Test User",
    email: str = "test@example.com",
    password_hash: str = "$2b$12$fakehash",
    role: UserRole = UserRole.staff,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock User object."""
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.full_name = full_name
    user.email = email
    user.password_hash = password_hash
    user.role = role
    user.is_active = is_active
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


def _create_service(
    user_repo: Optional[AsyncMock] = None,
) -> UserService:
    """Create a UserService with a mock repository."""
    return UserService(
        user_repo=user_repo or AsyncMock(spec=UserRepositoryInterface),
    )


# --- Create User Tests ---


class TestUserServiceCreateUser:
    """Tests for UserService.create_user()."""

    @pytest.mark.asyncio
    async def test_create_user_success(self) -> None:
        """Successful user creation returns the created user."""
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_email.return_value = None
        created_user = _make_user(email="new@example.com", full_name="New User")
        user_repo.create.return_value = created_user

        service = _create_service(user_repo=user_repo)

        with patch("app.services.user_service.hash_password", return_value="$2b$12$hashed"):
            result = await service.create_user(
                full_name="New User",
                email="new@example.com",
                password="password123",
                role=UserRole.staff,
            )

        assert result == created_user
        user_repo.get_by_email.assert_called_once_with("new@example.com")
        user_repo.create.assert_called_once_with(
            full_name="New User",
            email="new@example.com",
            password_hash="$2b$12$hashed",
            role=UserRole.staff,
        )

    @pytest.mark.asyncio
    async def test_create_user_hashes_password(self) -> None:
        """User creation hashes the password before storing."""
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_email.return_value = None
        user_repo.create.return_value = _make_user()

        service = _create_service(user_repo=user_repo)

        with patch(
            "app.services.user_service.hash_password", return_value="$2b$12$hashed"
        ) as mock_hash:
            await service.create_user(
                full_name="Test",
                email="test@example.com",
                password="mypassword",
                role=UserRole.admin,
            )

        mock_hash.assert_called_once_with("mypassword")

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email_raises_conflict(self) -> None:
        """Creating a user with an existing email raises ConflictException."""
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_email.return_value = _make_user(email="existing@example.com")

        service = _create_service(user_repo=user_repo)

        with pytest.raises(ConflictException) as exc_info:
            await service.create_user(
                full_name="Test",
                email="existing@example.com",
                password="password123",
                role=UserRole.staff,
            )

        assert "email already exists" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_create_user_short_password_raises_validation(self) -> None:
        """Creating a user with password < 8 chars raises ValidationException."""
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        service = _create_service(user_repo=user_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_user(
                full_name="Test",
                email="test@example.com",
                password="short",
                role=UserRole.staff,
            )

        assert any(e.field == "password" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_create_user_empty_name_raises_validation(self) -> None:
        """Creating a user with empty full_name raises ValidationException."""
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        service = _create_service(user_repo=user_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_user(
                full_name="",
                email="test@example.com",
                password="password123",
                role=UserRole.staff,
            )

        assert any(e.field == "full_name" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_create_user_name_too_long_raises_validation(self) -> None:
        """Creating a user with full_name > 100 chars raises ValidationException."""
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        service = _create_service(user_repo=user_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_user(
                full_name="A" * 101,
                email="test@example.com",
                password="password123",
                role=UserRole.staff,
            )

        assert any(e.field == "full_name" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_create_user_strips_full_name(self) -> None:
        """User creation strips whitespace from full_name."""
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_email.return_value = None
        user_repo.create.return_value = _make_user()

        service = _create_service(user_repo=user_repo)

        with patch("app.services.user_service.hash_password", return_value="$2b$12$hashed"):
            await service.create_user(
                full_name="  John Doe  ",
                email="john@example.com",
                password="password123",
                role=UserRole.staff,
            )

        call_kwargs = user_repo.create.call_args[1]
        assert call_kwargs["full_name"] == "John Doe"


# --- Update User Tests ---


class TestUserServiceUpdateUser:
    """Tests for UserService.update_user()."""

    @pytest.mark.asyncio
    async def test_update_user_success(self) -> None:
        """Successful user update returns the updated user."""
        user_id = uuid.uuid4()
        existing_user = _make_user(user_id=user_id, full_name="Old Name")
        updated_user = _make_user(user_id=user_id, full_name="New Name")

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = existing_user
        user_repo.update.return_value = updated_user

        service = _create_service(user_repo=user_repo)

        result = await service.update_user(user_id, full_name="New Name")

        assert result == updated_user
        user_repo.update.assert_called_once_with(user_id, full_name="New Name")

    @pytest.mark.asyncio
    async def test_update_user_not_found_raises_not_found(self) -> None:
        """Updating a non-existent user raises NotFoundException."""
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = None

        service = _create_service(user_repo=user_repo)

        with pytest.raises(NotFoundException):
            await service.update_user(uuid.uuid4(), full_name="New Name")

    @pytest.mark.asyncio
    async def test_update_user_email_uniqueness_check(self) -> None:
        """Updating email to an existing email raises ConflictException."""
        user_id = uuid.uuid4()
        existing_user = _make_user(user_id=user_id, email="old@example.com")
        other_user = _make_user(email="taken@example.com")

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = existing_user
        user_repo.get_by_email.return_value = other_user

        service = _create_service(user_repo=user_repo)

        with pytest.raises(ConflictException) as exc_info:
            await service.update_user(user_id, email="taken@example.com")

        assert "email already exists" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_update_user_same_email_no_conflict(self) -> None:
        """Updating with the same email does not trigger conflict check."""
        user_id = uuid.uuid4()
        existing_user = _make_user(user_id=user_id, email="same@example.com")
        updated_user = _make_user(user_id=user_id, full_name="Updated")

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = existing_user
        user_repo.update.return_value = updated_user

        service = _create_service(user_repo=user_repo)

        # Should not raise even though email is provided
        result = await service.update_user(user_id, email="same@example.com")

        assert result == updated_user
        # get_by_email should not be called since email didn't change
        user_repo.get_by_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_empty_name_raises_validation(self) -> None:
        """Updating with empty full_name raises ValidationException."""
        user_id = uuid.uuid4()
        existing_user = _make_user(user_id=user_id)

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = existing_user

        service = _create_service(user_repo=user_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.update_user(user_id, full_name="   ")

        assert any(e.field == "full_name" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_update_user_no_fields_returns_existing(self) -> None:
        """Updating with no fields returns the existing user unchanged."""
        user_id = uuid.uuid4()
        existing_user = _make_user(user_id=user_id)

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = existing_user

        service = _create_service(user_repo=user_repo)

        result = await service.update_user(user_id)

        assert result == existing_user
        user_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_user_multiple_fields(self) -> None:
        """Updating multiple fields passes all to repository."""
        user_id = uuid.uuid4()
        existing_user = _make_user(user_id=user_id, email="old@example.com")
        updated_user = _make_user(user_id=user_id)

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = existing_user
        user_repo.get_by_email.return_value = None
        user_repo.update.return_value = updated_user

        service = _create_service(user_repo=user_repo)

        await service.update_user(
            user_id,
            full_name="New Name",
            email="new@example.com",
            role=UserRole.admin,
            is_active=False,
        )

        user_repo.update.assert_called_once_with(
            user_id,
            full_name="New Name",
            email="new@example.com",
            role=UserRole.admin,
            is_active=False,
        )


# --- Reset Password Tests ---


class TestUserServiceResetPassword:
    """Tests for UserService.reset_password()."""

    @pytest.mark.asyncio
    async def test_reset_password_success(self) -> None:
        """Successful password reset hashes and updates the password."""
        user_id = uuid.uuid4()
        existing_user = _make_user(user_id=user_id)

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = existing_user
        user_repo.update.return_value = existing_user

        service = _create_service(user_repo=user_repo)

        with patch(
            "app.services.user_service.hash_password", return_value="$2b$12$newhash"
        ) as mock_hash:
            await service.reset_password(user_id, "newpassword123")

        mock_hash.assert_called_once_with("newpassword123")
        user_repo.update.assert_called_once_with(
            user_id, password_hash="$2b$12$newhash"
        )

    @pytest.mark.asyncio
    async def test_reset_password_short_password_raises_validation(self) -> None:
        """Resetting with password < 8 chars raises ValidationException."""
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        service = _create_service(user_repo=user_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.reset_password(uuid.uuid4(), "short")

        assert any(e.field == "password" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_reset_password_user_not_found_raises_not_found(self) -> None:
        """Resetting password for non-existent user raises NotFoundException."""
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = None

        service = _create_service(user_repo=user_repo)

        with pytest.raises(NotFoundException):
            await service.reset_password(uuid.uuid4(), "validpassword123")


# --- Deactivate User Tests ---


class TestUserServiceDeactivateUser:
    """Tests for UserService.deactivate_user()."""

    @pytest.mark.asyncio
    async def test_deactivate_user_success(self) -> None:
        """Successful deactivation sets is_active to false."""
        user_id = uuid.uuid4()
        existing_user = _make_user(user_id=user_id, is_active=True)
        deactivated_user = _make_user(user_id=user_id, is_active=False)

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = existing_user
        user_repo.update.return_value = deactivated_user

        service = _create_service(user_repo=user_repo)

        result = await service.deactivate_user(user_id)

        assert result == deactivated_user
        user_repo.update.assert_called_once_with(user_id, is_active=False)

    @pytest.mark.asyncio
    async def test_deactivate_user_not_found_raises_not_found(self) -> None:
        """Deactivating a non-existent user raises NotFoundException."""
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = None

        service = _create_service(user_repo=user_repo)

        with pytest.raises(NotFoundException):
            await service.deactivate_user(uuid.uuid4())


# --- List Users Tests ---


class TestUserServiceListUsers:
    """Tests for UserService.list_users()."""

    @pytest.mark.asyncio
    async def test_list_users_delegates_to_repository(self) -> None:
        """list_users passes filters and pagination to the repository."""
        users = [_make_user() for _ in range(3)]
        paginated_result = PaginatedResult(items=users, total_count=3)

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.return_value = paginated_result

        service = _create_service(user_repo=user_repo)

        filters = UserFilters(search="test", role=UserRole.staff, is_active=True)
        pagination = PaginationParams(page=1, page_size=20)

        result = await service.list_users(filters=filters, pagination=pagination)

        assert result == paginated_result
        user_repo.list.assert_called_once_with(
            filters=filters, pagination=pagination
        )

    @pytest.mark.asyncio
    async def test_list_users_empty_result(self) -> None:
        """list_users returns empty result when no users match."""
        paginated_result = PaginatedResult(items=[], total_count=0)

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.list.return_value = paginated_result

        service = _create_service(user_repo=user_repo)

        filters = UserFilters()
        pagination = PaginationParams(page=1, page_size=20)

        result = await service.list_users(filters=filters, pagination=pagination)

        assert result.items == []
        assert result.total_count == 0

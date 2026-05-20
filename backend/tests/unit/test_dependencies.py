"""Unit tests for core dependencies module."""

import os

# Set required env vars before importing app modules that trigger settings validation
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/testdb")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests")

import pytest

from app.core.dependencies import PaginationParams, get_pagination


class TestPaginationParams:
    """Tests for PaginationParams dataclass."""

    def test_default_offset_page_one(self):
        """Page 1 should have offset 0."""
        params = PaginationParams(page=1, page_size=20)
        assert params.offset == 0

    def test_offset_page_two(self):
        """Page 2 with page_size 20 should have offset 20."""
        params = PaginationParams(page=2, page_size=20)
        assert params.offset == 20

    def test_offset_page_three_custom_size(self):
        """Page 3 with page_size 50 should have offset 100."""
        params = PaginationParams(page=3, page_size=50)
        assert params.offset == 100

    def test_limit_equals_page_size(self):
        """Limit should always equal page_size."""
        params = PaginationParams(page=1, page_size=42)
        assert params.limit == 42

    def test_offset_formula(self):
        """Offset should be (page - 1) * page_size."""
        params = PaginationParams(page=5, page_size=10)
        assert params.offset == 40

    def test_limit_with_max_page_size(self):
        """Limit should work with max page_size of 100."""
        params = PaginationParams(page=1, page_size=100)
        assert params.limit == 100
        assert params.offset == 0


class TestGetPagination:
    """Tests for get_pagination dependency function."""

    @pytest.mark.asyncio
    async def test_default_values(self):
        """Should return defaults: page=1, page_size=20."""
        result = await get_pagination(page=1, page_size=20)
        assert result.page == 1
        assert result.page_size == 20
        assert result.offset == 0
        assert result.limit == 20

    @pytest.mark.asyncio
    async def test_custom_values(self):
        """Should accept custom page and page_size."""
        result = await get_pagination(page=3, page_size=50)
        assert result.page == 3
        assert result.page_size == 50
        assert result.offset == 100
        assert result.limit == 50

    @pytest.mark.asyncio
    async def test_minimum_page(self):
        """Should accept minimum page value of 1."""
        result = await get_pagination(page=1, page_size=1)
        assert result.page == 1
        assert result.page_size == 1
        assert result.offset == 0
        assert result.limit == 1

    @pytest.mark.asyncio
    async def test_maximum_page_size(self):
        """Should accept maximum page_size of 100."""
        result = await get_pagination(page=1, page_size=100)
        assert result.page_size == 100
        assert result.limit == 100


import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.dependencies import get_current_user, require_admin
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.schemas.enums import UserRole


def _make_user(
    user_id: uuid.UUID | None = None,
    role: UserRole = UserRole.staff,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock User object for testing."""
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.role = role
    user.is_active = is_active
    user.full_name = "Test User"
    user.email = "test@example.com"
    return user


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_active_user(self):
        """Should return user when token is valid and user is active."""
        user_id = uuid.uuid4()
        mock_user = _make_user(user_id=user_id, is_active=True)

        with patch(
            "app.core.dependencies.verify_access_token",
            return_value={"sub": str(user_id), "role": "staff"},
        ), patch(
            "app.repositories.user_repository.UserRepository"
        ) as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_by_id = AsyncMock(return_value=mock_user)

            result = await get_current_user(
                token="valid.jwt.token", session=AsyncMock()
            )

            assert result == mock_user
            mock_repo_instance.get_by_id.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_invalid_token_raises_unauthorized(self):
        """Should raise UnauthorizedException for invalid token."""
        with patch(
            "app.core.dependencies.verify_access_token",
            side_effect=ValueError("Invalid token"),
        ):
            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(token="invalid.token", session=AsyncMock())

            assert "Invalid or expired token" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_expired_token_raises_unauthorized(self):
        """Should raise UnauthorizedException for expired token."""
        with patch(
            "app.core.dependencies.verify_access_token",
            side_effect=ValueError("Token expired"),
        ):
            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(token="expired.token", session=AsyncMock())

            assert "Invalid or expired token" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_missing_sub_claim_raises_unauthorized(self):
        """Should raise UnauthorizedException when token has no sub claim."""
        with patch(
            "app.core.dependencies.verify_access_token",
            return_value={"role": "staff"},
        ):
            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(token="no.sub.token", session=AsyncMock())

            assert "missing subject" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_malformed_sub_claim_raises_unauthorized(self):
        """Should raise UnauthorizedException when sub is not a valid UUID."""
        with patch(
            "app.core.dependencies.verify_access_token",
            return_value={"sub": "not-a-uuid", "role": "staff"},
        ):
            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(
                    token="bad.sub.token", session=AsyncMock()
                )

            assert "malformed subject" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_user_not_found_raises_unauthorized(self):
        """Should raise UnauthorizedException when user doesn't exist."""
        user_id = uuid.uuid4()

        with patch(
            "app.core.dependencies.verify_access_token",
            return_value={"sub": str(user_id), "role": "staff"},
        ), patch(
            "app.repositories.user_repository.UserRepository"
        ) as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_by_id = AsyncMock(return_value=None)

            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(
                    token="valid.token", session=AsyncMock()
                )

            assert "User not found" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_inactive_user_raises_unauthorized(self):
        """Should raise UnauthorizedException when user is inactive."""
        user_id = uuid.uuid4()
        mock_user = _make_user(user_id=user_id, is_active=False)

        with patch(
            "app.core.dependencies.verify_access_token",
            return_value={"sub": str(user_id), "role": "staff"},
        ), patch(
            "app.repositories.user_repository.UserRepository"
        ) as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_by_id = AsyncMock(return_value=mock_user)

            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(
                    token="valid.token", session=AsyncMock()
                )

            assert "inactive" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_cookie_token_used_when_no_bearer(self):
        """Should return user when access_token cookie present and no Bearer header."""
        user_id = uuid.uuid4()
        mock_user = _make_user(user_id=user_id, is_active=True)

        with patch(
            "app.core.dependencies.verify_access_token",
            return_value={"sub": str(user_id), "role": "staff"},
        ), patch(
            "app.repositories.user_repository.UserRepository"
        ) as MockRepo:
            mock_repo_instance = MockRepo.return_value
            mock_repo_instance.get_by_id = AsyncMock(return_value=mock_user)

            result = await get_current_user(
                token=None,
                cookie_token="valid.cookie.token",
                session=AsyncMock(),
            )

            assert result == mock_user

    @pytest.mark.asyncio
    async def test_no_bearer_no_cookie_raises_unauthorized(self):
        """Should raise UnauthorizedException when both Bearer and cookie are missing."""
        with pytest.raises(UnauthorizedException) as exc_info:
            await get_current_user(
                token=None,
                cookie_token=None,
                session=AsyncMock(),
            )

        assert "Not authenticated" in exc_info.value.message


class TestRequireAdmin:
    """Tests for require_admin dependency."""

    @pytest.mark.asyncio
    async def test_admin_user_passes(self):
        """Should return user when role is admin."""
        admin_user = _make_user(role=UserRole.admin)

        result = await require_admin(current_user=admin_user)

        assert result == admin_user

    @pytest.mark.asyncio
    async def test_staff_user_raises_forbidden(self):
        """Should raise ForbiddenException when role is staff."""
        staff_user = _make_user(role=UserRole.staff)

        with pytest.raises(ForbiddenException) as exc_info:
            await require_admin(current_user=staff_user)

        assert "Admin access required" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_forbidden_has_403_status(self):
        """Should return 403 status code for non-admin users."""
        staff_user = _make_user(role=UserRole.staff)

        with pytest.raises(ForbiddenException) as exc_info:
            await require_admin(current_user=staff_user)

        assert exc_info.value.status_code == 403

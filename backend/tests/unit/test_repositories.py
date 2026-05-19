"""Unit tests for auth repository implementations.

Tests verify that repository methods correctly interact with the
SQLAlchemy session and construct proper queries.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.dependencies import PaginationParams
from app.domain.interfaces import (
    LoginAttemptRepositoryInterface,
    PaginatedResult,
    RefreshTokenRepositoryInterface,
    UserFilters,
    UserRepositoryInterface,
)
from app.repositories.login_attempt_repository import LoginAttemptRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.enums import UserRole


class TestUserRepositoryInterface:
    """Tests verifying UserRepository implements the interface correctly."""

    def test_implements_interface(self) -> None:
        """UserRepository should be a subclass of UserRepositoryInterface."""
        assert issubclass(UserRepository, UserRepositoryInterface)

    def test_constructor_accepts_session(self) -> None:
        """UserRepository should accept an AsyncSession in its constructor."""
        mock_session = AsyncMock()
        repo = UserRepository(session=mock_session)
        assert repo._session is mock_session


class TestRefreshTokenRepositoryInterface:
    """Tests verifying RefreshTokenRepository implements the interface correctly."""

    def test_implements_interface(self) -> None:
        """RefreshTokenRepository should be a subclass of RefreshTokenRepositoryInterface."""
        assert issubclass(RefreshTokenRepository, RefreshTokenRepositoryInterface)

    def test_constructor_accepts_session(self) -> None:
        """RefreshTokenRepository should accept an AsyncSession in its constructor."""
        mock_session = AsyncMock()
        repo = RefreshTokenRepository(session=mock_session)
        assert repo._session is mock_session


class TestLoginAttemptRepositoryInterface:
    """Tests verifying LoginAttemptRepository implements the interface correctly."""

    def test_implements_interface(self) -> None:
        """LoginAttemptRepository should be a subclass of LoginAttemptRepositoryInterface."""
        assert issubclass(LoginAttemptRepository, LoginAttemptRepositoryInterface)

    def test_constructor_accepts_session(self) -> None:
        """LoginAttemptRepository should accept an AsyncSession in its constructor."""
        mock_session = AsyncMock()
        repo = LoginAttemptRepository(session=mock_session)
        assert repo._session is mock_session


class TestUserRepositoryCreate:
    """Tests for UserRepository.create method."""

    @pytest.mark.asyncio
    async def test_create_adds_user_to_session(self) -> None:
        """create() should add a User instance to the session."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        repo = UserRepository(session=mock_session)

        await repo.create(
            full_name="Test User",
            email="test@example.com",
            password_hash="hashed_password",
            role=UserRole.staff,
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_sets_correct_fields(self) -> None:
        """create() should set all provided fields on the User instance."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        repo = UserRepository(session=mock_session)

        await repo.create(
            full_name="Admin User",
            email="admin@example.com",
            password_hash="bcrypt_hash",
            role=UserRole.admin,
        )

        added_user = mock_session.add.call_args[0][0]
        assert added_user.full_name == "Admin User"
        assert added_user.email == "admin@example.com"
        assert added_user.password_hash == "bcrypt_hash"
        assert added_user.role == UserRole.admin


class TestUserRepositoryGetByEmail:
    """Tests for UserRepository.get_by_email method."""

    @pytest.mark.asyncio
    async def test_get_by_email_executes_query(self) -> None:
        """get_by_email() should execute a select query on the session."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserRepository(session=mock_session)
        result = await repo.get_by_email("test@example.com")

        mock_session.execute.assert_called_once()
        assert result is None


class TestUserRepositoryGetById:
    """Tests for UserRepository.get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_executes_query(self) -> None:
        """get_by_id() should execute a select query on the session."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserRepository(session=mock_session)
        user_id = uuid.uuid4()
        result = await repo.get_by_id(user_id)

        mock_session.execute.assert_called_once()
        assert result is None


class TestUserRepositoryUpdate:
    """Tests for UserRepository.update method."""

    @pytest.mark.asyncio
    async def test_update_returns_none_for_missing_user(self) -> None:
        """update() should return None if user is not found."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        repo = UserRepository(session=mock_session)
        result = await repo.update(uuid.uuid4(), full_name="New Name")

        assert result is None


class TestUserRepositoryList:
    """Tests for UserRepository.list method."""

    @pytest.mark.asyncio
    async def test_list_returns_paginated_result(self) -> None:
        """list() should return a PaginatedResult instance."""
        mock_session = AsyncMock()

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        # Mock list query
        mock_list_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_list_result.scalars.return_value = mock_scalars

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        repo = UserRepository(session=mock_session)
        filters = UserFilters()
        pagination = PaginationParams(page=1, page_size=20)

        result = await repo.list(filters=filters, pagination=pagination)

        assert isinstance(result, PaginatedResult)
        assert result.items == []
        assert result.total_count == 0


class TestRefreshTokenRepositoryCreate:
    """Tests for RefreshTokenRepository.create method."""

    @pytest.mark.asyncio
    async def test_create_adds_token_to_session(self) -> None:
        """create() should add a RefreshToken instance to the session."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        repo = RefreshTokenRepository(session=mock_session)

        user_id = uuid.uuid4()
        expires_at = datetime.now(timezone.utc)

        await repo.create(
            user_id=user_id,
            token_hash="hashed_token",
            token_family="family_id",
            expires_at=expires_at,
        )

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

        added_token = mock_session.add.call_args[0][0]
        assert added_token.user_id == user_id
        assert added_token.token_hash == "hashed_token"
        assert added_token.token_family == "family_id"
        assert added_token.expires_at == expires_at


class TestRefreshTokenRepositoryRevoke:
    """Tests for RefreshTokenRepository revocation methods."""

    @pytest.mark.asyncio
    async def test_revoke_executes_update(self) -> None:
        """revoke() should execute an update statement."""
        mock_session = AsyncMock()
        repo = RefreshTokenRepository(session=mock_session)

        token_id = uuid.uuid4()
        await repo.revoke(token_id)

        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_family_executes_update(self) -> None:
        """revoke_family() should execute an update statement."""
        mock_session = AsyncMock()
        repo = RefreshTokenRepository(session=mock_session)

        await repo.revoke_family("family_123")

        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_all_for_user_executes_update(self) -> None:
        """revoke_all_for_user() should execute an update statement."""
        mock_session = AsyncMock()
        repo = RefreshTokenRepository(session=mock_session)

        user_id = uuid.uuid4()
        await repo.revoke_all_for_user(user_id)

        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()


class TestLoginAttemptRepositoryCreate:
    """Tests for LoginAttemptRepository.create method."""

    @pytest.mark.asyncio
    async def test_create_adds_attempt_to_session(self) -> None:
        """create() should add a LoginAttempt instance to the session."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        repo = LoginAttemptRepository(session=mock_session)

        user_id = uuid.uuid4()
        await repo.create(user_id=user_id, success=False)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

        added_attempt = mock_session.add.call_args[0][0]
        assert added_attempt.user_id == user_id
        assert added_attempt.success is False


class TestLoginAttemptRepositoryGetRecentFailures:
    """Tests for LoginAttemptRepository.get_recent_failures method."""

    @pytest.mark.asyncio
    async def test_get_recent_failures_executes_query(self) -> None:
        """get_recent_failures() should execute a select query."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = LoginAttemptRepository(session=mock_session)
        user_id = uuid.uuid4()
        since = datetime.now(timezone.utc)

        result = await repo.get_recent_failures(user_id=user_id, since=since)

        mock_session.execute.assert_called_once()
        assert result == []


class TestPaginatedResult:
    """Tests for the PaginatedResult container."""

    def test_stores_items_and_count(self) -> None:
        """PaginatedResult should store items and total_count."""
        items = [1, 2, 3]
        result = PaginatedResult(items=items, total_count=10)
        assert result.items == [1, 2, 3]
        assert result.total_count == 10


class TestUserFilters:
    """Tests for the UserFilters container."""

    def test_default_filters_are_none(self) -> None:
        """UserFilters should default all fields to None."""
        filters = UserFilters()
        assert filters.search is None
        assert filters.role is None
        assert filters.is_active is None

    def test_filters_accept_values(self) -> None:
        """UserFilters should accept search, role, and is_active values."""
        filters = UserFilters(
            search="test",
            role=UserRole.admin,
            is_active=True,
        )
        assert filters.search == "test"
        assert filters.role == UserRole.admin
        assert filters.is_active is True

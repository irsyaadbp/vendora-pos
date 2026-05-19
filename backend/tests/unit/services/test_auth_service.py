"""Unit tests for AuthService."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import AccountLockedException, UnauthorizedException
from app.domain.interfaces import (
    LoginAttemptRepositoryInterface,
    RefreshTokenRepositoryInterface,
    UserRepositoryInterface,
)
from app.schemas.enums import UserRole
from app.services.auth_service import AuthService, TokenPair


# --- Helpers ---


def _make_user(
    user_id: Optional[uuid.UUID] = None,
    email: str = "test@example.com",
    password_hash: str = "$2b$12$fakehash",
    role: UserRole = UserRole.staff,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock User object."""
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.full_name = "Test User"
    user.email = email
    user.password_hash = password_hash
    user.role = role
    user.is_active = is_active
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


def _make_refresh_token(
    user_id: uuid.UUID,
    token_hash: str = "hashed_token",
    token_family: str = "family-123",
    is_revoked: bool = False,
    expires_at: Optional[datetime] = None,
) -> MagicMock:
    """Create a mock RefreshToken object."""
    token = MagicMock()
    token.id = uuid.uuid4()
    token.user_id = user_id
    token.token_hash = token_hash
    token.token_family = token_family
    token.is_revoked = is_revoked
    token.expires_at = expires_at or (datetime.now(timezone.utc) + timedelta(days=7))
    token.created_at = datetime.now(timezone.utc)
    return token


def _make_login_attempt(user_id: uuid.UUID, success: bool = False) -> MagicMock:
    """Create a mock LoginAttempt object."""
    attempt = MagicMock()
    attempt.id = uuid.uuid4()
    attempt.user_id = user_id
    attempt.success = success
    attempt.attempted_at = datetime.now(timezone.utc)
    return attempt


def _create_service(
    user_repo: Optional[AsyncMock] = None,
    refresh_token_repo: Optional[AsyncMock] = None,
    login_attempt_repo: Optional[AsyncMock] = None,
) -> AuthService:
    """Create an AuthService with mock repositories."""
    return AuthService(
        user_repo=user_repo or AsyncMock(spec=UserRepositoryInterface),
        refresh_token_repo=refresh_token_repo or AsyncMock(spec=RefreshTokenRepositoryInterface),
        login_attempt_repo=login_attempt_repo or AsyncMock(spec=LoginAttemptRepositoryInterface),
    )


# --- Mock settings ---

_MOCK_SETTINGS_PATCH = patch(
    "app.services.auth_service.get_settings",
    return_value=type(
        "MockSettings",
        (),
        {
            "MAX_LOGIN_ATTEMPTS": 5,
            "LOGIN_LOCKOUT_MINUTES": 15,
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": 15,
            "JWT_REFRESH_TOKEN_EXPIRE_DAYS": 7,
            "JWT_SECRET": "test-secret",
        },
    )(),
)


# --- Login Tests ---


class TestAuthServiceLogin:
    """Tests for AuthService.login()."""

    @pytest.mark.asyncio
    async def test_login_success_returns_token_pair(self) -> None:
        """Successful login returns a TokenPair with access and refresh tokens."""
        user = _make_user()
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_email.return_value = user

        login_attempt_repo = AsyncMock(spec=LoginAttemptRepositoryInterface)
        login_attempt_repo.get_recent_failures.return_value = []
        login_attempt_repo.create.return_value = _make_login_attempt(user.id, success=True)

        refresh_token_repo = AsyncMock(spec=RefreshTokenRepositoryInterface)
        refresh_token_repo.create.return_value = _make_refresh_token(user.id)

        service = _create_service(
            user_repo=user_repo,
            refresh_token_repo=refresh_token_repo,
            login_attempt_repo=login_attempt_repo,
        )

        with _MOCK_SETTINGS_PATCH, patch(
            "app.services.auth_service.verify_password", return_value=True
        ):
            result = await service.login("test@example.com", "password123")

        assert isinstance(result, TokenPair)
        assert result.access_token is not None
        assert result.refresh_token is not None

    @pytest.mark.asyncio
    async def test_login_invalid_email_raises_unauthorized(self) -> None:
        """Login with non-existent email raises UnauthorizedException."""
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_email.return_value = None

        service = _create_service(user_repo=user_repo)

        with _MOCK_SETTINGS_PATCH, pytest.raises(UnauthorizedException) as exc_info:
            await service.login("nonexistent@example.com", "password123")

        assert "Invalid email or password" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_login_invalid_password_raises_unauthorized(self) -> None:
        """Login with wrong password raises UnauthorizedException and records failure."""
        user = _make_user()
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_email.return_value = user

        login_attempt_repo = AsyncMock(spec=LoginAttemptRepositoryInterface)
        login_attempt_repo.get_recent_failures.return_value = []
        login_attempt_repo.create.return_value = _make_login_attempt(user.id, success=False)

        service = _create_service(
            user_repo=user_repo,
            login_attempt_repo=login_attempt_repo,
        )

        with _MOCK_SETTINGS_PATCH, patch(
            "app.services.auth_service.verify_password", return_value=False
        ), pytest.raises(UnauthorizedException) as exc_info:
            await service.login("test@example.com", "wrongpassword")

        assert "Invalid email or password" in str(exc_info.value.message)
        login_attempt_repo.create.assert_called_once_with(
            user_id=user.id, success=False
        )

    @pytest.mark.asyncio
    async def test_login_deactivated_user_raises_unauthorized(self) -> None:
        """Login for deactivated user raises UnauthorizedException and revokes tokens."""
        user = _make_user(is_active=False)
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_email.return_value = user

        refresh_token_repo = AsyncMock(spec=RefreshTokenRepositoryInterface)

        service = _create_service(
            user_repo=user_repo,
            refresh_token_repo=refresh_token_repo,
        )

        with _MOCK_SETTINGS_PATCH, pytest.raises(UnauthorizedException):
            await service.login("test@example.com", "password123")

        refresh_token_repo.revoke_all_for_user.assert_called_once_with(user.id)

    @pytest.mark.asyncio
    async def test_login_locked_account_raises_account_locked(self) -> None:
        """Login for locked account raises AccountLockedException."""
        user = _make_user()
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_email.return_value = user

        # 5 recent failures = locked
        failures = [_make_login_attempt(user.id) for _ in range(5)]
        login_attempt_repo = AsyncMock(spec=LoginAttemptRepositoryInterface)
        login_attempt_repo.get_recent_failures.return_value = failures

        service = _create_service(
            user_repo=user_repo,
            login_attempt_repo=login_attempt_repo,
        )

        with _MOCK_SETTINGS_PATCH, pytest.raises(AccountLockedException):
            await service.login("test@example.com", "password123")

    @pytest.mark.asyncio
    async def test_login_stores_hashed_refresh_token(self) -> None:
        """Successful login stores a hashed refresh token with token family."""
        user = _make_user()
        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_email.return_value = user

        login_attempt_repo = AsyncMock(spec=LoginAttemptRepositoryInterface)
        login_attempt_repo.get_recent_failures.return_value = []
        login_attempt_repo.create.return_value = _make_login_attempt(user.id, success=True)

        refresh_token_repo = AsyncMock(spec=RefreshTokenRepositoryInterface)
        refresh_token_repo.create.return_value = _make_refresh_token(user.id)

        service = _create_service(
            user_repo=user_repo,
            refresh_token_repo=refresh_token_repo,
            login_attempt_repo=login_attempt_repo,
        )

        with _MOCK_SETTINGS_PATCH, patch(
            "app.services.auth_service.verify_password", return_value=True
        ):
            result = await service.login("test@example.com", "password123")

        # Verify refresh token repo was called with hashed token
        refresh_token_repo.create.assert_called_once()
        call_kwargs = refresh_token_repo.create.call_args[1]
        assert call_kwargs["user_id"] == user.id
        assert call_kwargs["token_hash"] != result.refresh_token  # stored hash != plaintext
        assert call_kwargs["token_family"] is not None
        assert call_kwargs["expires_at"] is not None


# --- Refresh Tests ---


class TestAuthServiceRefresh:
    """Tests for AuthService.refresh()."""

    @pytest.mark.asyncio
    async def test_refresh_success_returns_new_token_pair(self) -> None:
        """Valid refresh token returns a new token pair."""
        user = _make_user()
        stored_token = _make_refresh_token(user.id)

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = user

        refresh_token_repo = AsyncMock(spec=RefreshTokenRepositoryInterface)
        refresh_token_repo.get_by_token_hash.return_value = stored_token
        refresh_token_repo.create.return_value = _make_refresh_token(user.id)

        service = _create_service(
            user_repo=user_repo,
            refresh_token_repo=refresh_token_repo,
        )

        with _MOCK_SETTINGS_PATCH, patch(
            "app.services.auth_service.hash_refresh_token",
            return_value=stored_token.token_hash,
        ):
            result = await service.refresh("some-refresh-token")

        assert isinstance(result, TokenPair)
        assert result.access_token is not None
        assert result.refresh_token is not None

    @pytest.mark.asyncio
    async def test_refresh_revokes_old_token(self) -> None:
        """Refresh revokes the old token before issuing a new one."""
        user = _make_user()
        stored_token = _make_refresh_token(user.id)

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = user

        refresh_token_repo = AsyncMock(spec=RefreshTokenRepositoryInterface)
        refresh_token_repo.get_by_token_hash.return_value = stored_token
        refresh_token_repo.create.return_value = _make_refresh_token(user.id)

        service = _create_service(
            user_repo=user_repo,
            refresh_token_repo=refresh_token_repo,
        )

        with _MOCK_SETTINGS_PATCH, patch(
            "app.services.auth_service.hash_refresh_token",
            return_value=stored_token.token_hash,
        ):
            await service.refresh("some-refresh-token")

        refresh_token_repo.revoke.assert_called_once_with(stored_token.id)

    @pytest.mark.asyncio
    async def test_refresh_preserves_token_family(self) -> None:
        """New refresh token uses the same token family as the old one."""
        user = _make_user()
        stored_token = _make_refresh_token(user.id, token_family="my-family")

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = user

        refresh_token_repo = AsyncMock(spec=RefreshTokenRepositoryInterface)
        refresh_token_repo.get_by_token_hash.return_value = stored_token
        refresh_token_repo.create.return_value = _make_refresh_token(user.id)

        service = _create_service(
            user_repo=user_repo,
            refresh_token_repo=refresh_token_repo,
        )

        with _MOCK_SETTINGS_PATCH, patch(
            "app.services.auth_service.hash_refresh_token",
            return_value=stored_token.token_hash,
        ):
            await service.refresh("some-refresh-token")

        call_kwargs = refresh_token_repo.create.call_args[1]
        assert call_kwargs["token_family"] == "my-family"

    @pytest.mark.asyncio
    async def test_refresh_invalid_token_raises_unauthorized(self) -> None:
        """Refresh with unknown token raises UnauthorizedException."""
        refresh_token_repo = AsyncMock(spec=RefreshTokenRepositoryInterface)
        refresh_token_repo.get_by_token_hash.return_value = None

        service = _create_service(refresh_token_repo=refresh_token_repo)

        with _MOCK_SETTINGS_PATCH, pytest.raises(UnauthorizedException):
            await service.refresh("invalid-token")

    @pytest.mark.asyncio
    async def test_refresh_revoked_token_invalidates_family(self) -> None:
        """Refresh with already-revoked token invalidates entire family (reuse detection)."""
        user = _make_user()
        stored_token = _make_refresh_token(
            user.id, token_family="compromised-family", is_revoked=True
        )

        refresh_token_repo = AsyncMock(spec=RefreshTokenRepositoryInterface)
        refresh_token_repo.get_by_token_hash.return_value = stored_token

        service = _create_service(refresh_token_repo=refresh_token_repo)

        with _MOCK_SETTINGS_PATCH, patch(
            "app.services.auth_service.hash_refresh_token",
            return_value=stored_token.token_hash,
        ), pytest.raises(UnauthorizedException):
            await service.refresh("reused-token")

        refresh_token_repo.revoke_family.assert_called_once_with("compromised-family")

    @pytest.mark.asyncio
    async def test_refresh_expired_token_invalidates_family(self) -> None:
        """Refresh with expired token invalidates entire family."""
        user = _make_user()
        stored_token = _make_refresh_token(
            user.id,
            token_family="expired-family",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        refresh_token_repo = AsyncMock(spec=RefreshTokenRepositoryInterface)
        refresh_token_repo.get_by_token_hash.return_value = stored_token

        service = _create_service(refresh_token_repo=refresh_token_repo)

        with _MOCK_SETTINGS_PATCH, patch(
            "app.services.auth_service.hash_refresh_token",
            return_value=stored_token.token_hash,
        ), pytest.raises(UnauthorizedException):
            await service.refresh("expired-token")

        refresh_token_repo.revoke_family.assert_called_once_with("expired-family")

    @pytest.mark.asyncio
    async def test_refresh_deactivated_user_revokes_all_tokens(self) -> None:
        """Refresh for deactivated user revokes all their tokens."""
        user = _make_user(is_active=False)
        stored_token = _make_refresh_token(user.id)

        user_repo = AsyncMock(spec=UserRepositoryInterface)
        user_repo.get_by_id.return_value = user

        refresh_token_repo = AsyncMock(spec=RefreshTokenRepositoryInterface)
        refresh_token_repo.get_by_token_hash.return_value = stored_token

        service = _create_service(
            user_repo=user_repo,
            refresh_token_repo=refresh_token_repo,
        )

        with _MOCK_SETTINGS_PATCH, patch(
            "app.services.auth_service.hash_refresh_token",
            return_value=stored_token.token_hash,
        ), pytest.raises(UnauthorizedException):
            await service.refresh("some-token")

        refresh_token_repo.revoke_all_for_user.assert_called_once_with(user.id)


# --- Logout Tests ---


class TestAuthServiceLogout:
    """Tests for AuthService.logout()."""

    @pytest.mark.asyncio
    async def test_logout_revokes_token(self) -> None:
        """Logout revokes the refresh token."""
        user = _make_user()
        stored_token = _make_refresh_token(user.id)

        refresh_token_repo = AsyncMock(spec=RefreshTokenRepositoryInterface)
        refresh_token_repo.get_by_token_hash.return_value = stored_token

        service = _create_service(refresh_token_repo=refresh_token_repo)

        with patch(
            "app.services.auth_service.hash_refresh_token",
            return_value=stored_token.token_hash,
        ):
            await service.logout("some-refresh-token")

        refresh_token_repo.revoke.assert_called_once_with(stored_token.id)

    @pytest.mark.asyncio
    async def test_logout_unknown_token_does_nothing(self) -> None:
        """Logout with unknown token does not raise an error."""
        refresh_token_repo = AsyncMock(spec=RefreshTokenRepositoryInterface)
        refresh_token_repo.get_by_token_hash.return_value = None

        service = _create_service(refresh_token_repo=refresh_token_repo)

        with patch(
            "app.services.auth_service.hash_refresh_token",
            return_value="unknown-hash",
        ):
            # Should not raise
            await service.logout("unknown-token")

        refresh_token_repo.revoke.assert_not_called()

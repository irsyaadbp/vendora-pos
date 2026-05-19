"""Property-based tests for authentication.

Feature: vendora-pos-foundation
Property 1: Password hashing uses bcrypt with sufficient cost
Property 2: JWT token expiration matches configuration
Property 3: Refresh token rotation invalidates previous token
Property 4: Token family invalidation on compromised refresh token
Property 5: Refresh tokens stored in hashed form
Property 6: Deactivated user authentication rejection
Property 7: Account lockout after consecutive failures
Property 10: Invalid credentials return generic error

Validates: Requirements 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.9, 3.10, 3.11

These tests verify the security module functions and AuthService behavior
using property-based testing with Hypothesis strategies.
"""

import hashlib
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

# Set environment variables before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-property-tests-minimum-length")

from app.core.config import Settings
from app.core.exceptions import AccountLockedException, UnauthorizedException
from app.infrastructure.security import (
    create_access_token,
    generate_refresh_token,
    generate_token_family,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.login_attempt import LoginAttempt
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.enums import UserRole
from app.services.auth_service import AuthService, TokenPair


# --- Strategies ---

password_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters="\x00",
        max_codepoint=127,  # ASCII only to stay within 72-byte bcrypt limit
    ),
    min_size=8,
    max_size=72,  # bcrypt max input length
)

user_id_strategy = st.uuids()

role_strategy = st.sampled_from([UserRole.admin, UserRole.staff])

expires_minutes_strategy = st.integers(min_value=1, max_value=1440)

email_strategy = st.emails()


# --- Property 1: Password hashing uses bcrypt with sufficient cost ---


class TestPasswordHashingBcryptCost:
    """**Validates: Requirements 3.3**

    Property 1: For any password, the hash is valid bcrypt with cost >= 12.
    The hash_password function SHALL produce a valid bcrypt hash with a
    cost factor of at least 12, and the original plaintext SHALL NOT
    appear in the stored hash.
    """

    @given(password=password_strategy)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_hash_is_valid_bcrypt_format(self, password: str):
        """For any password, hash_password produces a valid bcrypt hash string."""
        hashed = hash_password(password)
        # bcrypt hashes start with $2b$ (or $2a$, $2y$)
        assert re.match(r"^\$2[aby]\$\d{2}\$", hashed), (
            f"Hash '{hashed}' is not a valid bcrypt format"
        )

    @given(password=password_strategy)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_hash_cost_factor_at_least_12(self, password: str):
        """For any password, the bcrypt cost factor is at least 12."""
        hashed = hash_password(password)
        # Extract cost factor from bcrypt hash: $2b$12$...
        match = re.match(r"^\$2[aby]\$(\d{2})\$", hashed)
        assert match is not None
        cost = int(match.group(1))
        assert cost >= 12, (
            f"Bcrypt cost factor {cost} is less than required minimum of 12"
        )

    @given(password=password_strategy)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_plaintext_not_in_hash(self, password: str):
        """For any password, the plaintext does not appear in the hash."""
        assume(len(password) > 3)  # Very short passwords might coincidentally match
        hashed = hash_password(password)
        assert password not in hashed, (
            "Plaintext password must not appear in the hash"
        )

    @given(password=password_strategy)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_hash_verifies_correctly(self, password: str):
        """For any password, verify_password returns True for the correct password."""
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    @given(
        password=password_strategy,
        wrong_password=password_strategy,
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_hash_rejects_wrong_password(self, password: str, wrong_password: str):
        """For any two different passwords, verify_password returns False."""
        assume(password != wrong_password)
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False


# --- Property 2: JWT token expiration matches configuration ---


class TestJWTTokenExpiration:
    """**Validates: Requirements 3.4, 3.5**

    Property 2: Token exp = iat + configured duration.
    For any generated JWT access token, the token's expiration claim
    SHALL equal the issuance time plus the configured expiration duration.
    """

    @given(
        user_id=user_id_strategy,
        role=role_strategy,
        expires_minutes=expires_minutes_strategy,
    )
    @settings(max_examples=50)
    def test_access_token_expiration_matches_config(
        self, user_id: uuid.UUID, role: UserRole, expires_minutes: int
    ):
        """For any user_id, role, and expiry duration, the JWT exp claim
        equals iat + configured minutes."""
        from jose import jwt as jose_jwt

        from app.core.config import get_settings

        token = create_access_token(
            user_id=str(user_id),
            role=role.value,
            expires_minutes=expires_minutes,
        )

        # Use the same secret that create_access_token uses
        actual_settings = get_settings()

        payload = jose_jwt.decode(
            token, actual_settings.JWT_SECRET, algorithms=["HS256"]
        )

        iat = payload["iat"]
        exp = payload["exp"]
        expected_duration = expires_minutes * 60

        # Allow 2 second tolerance for execution time
        actual_duration = exp - iat
        assert abs(actual_duration - expected_duration) <= 2, (
            f"Token duration {actual_duration}s != expected {expected_duration}s "
            f"(tolerance: 2s)"
        )

    @given(user_id=user_id_strategy, role=role_strategy)
    @settings(max_examples=30)
    def test_access_token_contains_required_claims(
        self, user_id: uuid.UUID, role: UserRole
    ):
        """For any user_id and role, the JWT contains sub, role, exp, iat claims."""
        from jose import jwt as jose_jwt

        from app.core.config import get_settings

        token = create_access_token(
            user_id=str(user_id),
            role=role.value,
            expires_minutes=15,
        )

        # Use the same secret that create_access_token uses
        actual_settings = get_settings()

        payload = jose_jwt.decode(
            token, actual_settings.JWT_SECRET, algorithms=["HS256"]
        )

        assert payload["sub"] == str(user_id)
        assert payload["role"] == role.value
        assert "exp" in payload
        assert "iat" in payload


# --- Property 3: Refresh token rotation invalidates previous token ---


class TestRefreshTokenRotation:
    """**Validates: Requirements 3.6**

    Property 3: After refresh, old token is revoked.
    For any valid refresh token that is used to obtain a new access token,
    the system SHALL issue a new refresh token and the previous refresh
    token SHALL no longer be accepted.
    """

    @given(user_id=user_id_strategy, role=role_strategy)
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_refresh_revokes_old_token(
        self, user_id: uuid.UUID, role: UserRole
    ):
        """After a successful refresh, the old token's revoke method is called."""
        # Setup mocks
        user_repo = AsyncMock()
        refresh_token_repo = AsyncMock()
        login_attempt_repo = AsyncMock()

        # Create a mock user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.role = role
        mock_user.is_active = True

        # Create a mock stored token (not revoked, not expired)
        token_family = generate_token_family()
        original_token = generate_refresh_token()
        original_hash = hash_refresh_token(original_token)

        mock_stored_token = MagicMock()
        mock_stored_token.id = uuid.uuid4()
        mock_stored_token.user_id = user_id
        mock_stored_token.token_hash = original_hash
        mock_stored_token.token_family = token_family
        mock_stored_token.is_revoked = False
        mock_stored_token.expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        refresh_token_repo.get_by_token_hash.return_value = mock_stored_token
        refresh_token_repo.revoke.return_value = None
        refresh_token_repo.create.return_value = MagicMock()
        user_repo.get_by_id.return_value = mock_user

        service = AuthService(user_repo, refresh_token_repo, login_attempt_repo)

        result = await service.refresh(original_token)

        # Verify old token was revoked
        refresh_token_repo.revoke.assert_called_once_with(mock_stored_token.id)

        # Verify new token pair is returned
        assert result.access_token is not None
        assert result.refresh_token is not None
        assert result.refresh_token != original_token

    @given(user_id=user_id_strategy, role=role_strategy)
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_refresh_creates_new_token_in_same_family(
        self, user_id: uuid.UUID, role: UserRole
    ):
        """After refresh, a new token is created in the same token family."""
        user_repo = AsyncMock()
        refresh_token_repo = AsyncMock()
        login_attempt_repo = AsyncMock()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.role = role
        mock_user.is_active = True

        token_family = generate_token_family()
        original_token = generate_refresh_token()
        original_hash = hash_refresh_token(original_token)

        mock_stored_token = MagicMock()
        mock_stored_token.id = uuid.uuid4()
        mock_stored_token.user_id = user_id
        mock_stored_token.token_hash = original_hash
        mock_stored_token.token_family = token_family
        mock_stored_token.is_revoked = False
        mock_stored_token.expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        refresh_token_repo.get_by_token_hash.return_value = mock_stored_token
        refresh_token_repo.revoke.return_value = None
        refresh_token_repo.create.return_value = MagicMock()
        user_repo.get_by_id.return_value = mock_user

        service = AuthService(user_repo, refresh_token_repo, login_attempt_repo)

        await service.refresh(original_token)

        # Verify new token was created with same family
        create_call = refresh_token_repo.create.call_args
        assert create_call.kwargs["token_family"] == token_family
        assert create_call.kwargs["user_id"] == user_id


# --- Property 4: Token family invalidation on compromised refresh token ---


class TestTokenFamilyInvalidation:
    """**Validates: Requirements 3.7**

    Property 4: Revoked token triggers family invalidation.
    For any expired, revoked, or tampered refresh token submitted for
    refresh, the system SHALL reject the request and invalidate all
    refresh tokens belonging to the same token family.
    """

    @given(user_id=user_id_strategy)
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_revoked_token_triggers_family_invalidation(
        self, user_id: uuid.UUID
    ):
        """When a revoked token is used, the entire family is invalidated."""
        user_repo = AsyncMock()
        refresh_token_repo = AsyncMock()
        login_attempt_repo = AsyncMock()

        token_family = generate_token_family()
        compromised_token = generate_refresh_token()
        compromised_hash = hash_refresh_token(compromised_token)

        mock_stored_token = MagicMock()
        mock_stored_token.id = uuid.uuid4()
        mock_stored_token.user_id = user_id
        mock_stored_token.token_hash = compromised_hash
        mock_stored_token.token_family = token_family
        mock_stored_token.is_revoked = True  # Already revoked = reuse detected
        mock_stored_token.expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        refresh_token_repo.get_by_token_hash.return_value = mock_stored_token
        refresh_token_repo.revoke_family.return_value = None

        service = AuthService(user_repo, refresh_token_repo, login_attempt_repo)

        with pytest.raises(UnauthorizedException):
            await service.refresh(compromised_token)

        # Verify entire family was invalidated
        refresh_token_repo.revoke_family.assert_called_once_with(token_family)

    @given(user_id=user_id_strategy)
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_expired_token_triggers_family_invalidation(
        self, user_id: uuid.UUID
    ):
        """When an expired token is used, the entire family is invalidated."""
        user_repo = AsyncMock()
        refresh_token_repo = AsyncMock()
        login_attempt_repo = AsyncMock()

        token_family = generate_token_family()
        expired_token = generate_refresh_token()
        expired_hash = hash_refresh_token(expired_token)

        mock_stored_token = MagicMock()
        mock_stored_token.id = uuid.uuid4()
        mock_stored_token.user_id = user_id
        mock_stored_token.token_hash = expired_hash
        mock_stored_token.token_family = token_family
        mock_stored_token.is_revoked = False
        mock_stored_token.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        refresh_token_repo.get_by_token_hash.return_value = mock_stored_token
        refresh_token_repo.revoke_family.return_value = None

        service = AuthService(user_repo, refresh_token_repo, login_attempt_repo)

        with pytest.raises(UnauthorizedException):
            await service.refresh(expired_token)

        # Verify entire family was invalidated
        refresh_token_repo.revoke_family.assert_called_once_with(token_family)

    @given(user_id=user_id_strategy)
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_nonexistent_token_raises_unauthorized(
        self, user_id: uuid.UUID
    ):
        """When a token hash is not found in the database, raise Unauthorized."""
        user_repo = AsyncMock()
        refresh_token_repo = AsyncMock()
        login_attempt_repo = AsyncMock()

        fake_token = generate_refresh_token()
        refresh_token_repo.get_by_token_hash.return_value = None

        service = AuthService(user_repo, refresh_token_repo, login_attempt_repo)

        with pytest.raises(UnauthorizedException):
            await service.refresh(fake_token)


# --- Property 5: Refresh tokens stored in hashed form ---


class TestRefreshTokenHashedStorage:
    """**Validates: Requirements 3.9**

    Property 5: Stored value != plaintext.
    For any refresh token stored in the database, the stored value SHALL
    NOT equal the plaintext token value, and SHALL be a valid hash that
    can verify the original token.
    """

    @given(st.data())
    @settings(max_examples=50)
    def test_hashed_token_differs_from_plaintext(self, data):
        """For any generated refresh token, the hash differs from plaintext."""
        token = generate_refresh_token()
        hashed = hash_refresh_token(token)
        assert hashed != token, (
            "Stored token hash must not equal the plaintext token"
        )

    @given(st.data())
    @settings(max_examples=50)
    def test_hashed_token_is_valid_sha256(self, data):
        """For any generated refresh token, the hash is a valid SHA-256 hex digest."""
        token = generate_refresh_token()
        hashed = hash_refresh_token(token)
        # SHA-256 hex digest is 64 characters
        assert len(hashed) == 64, (
            f"Hash length {len(hashed)} != expected 64 for SHA-256"
        )
        assert re.match(r"^[0-9a-f]{64}$", hashed), (
            "Hash must be a valid lowercase hex string"
        )

    @given(st.data())
    @settings(max_examples=50)
    def test_hashed_token_is_deterministic(self, data):
        """For any token, hashing it twice produces the same result."""
        token = generate_refresh_token()
        hash1 = hash_refresh_token(token)
        hash2 = hash_refresh_token(token)
        assert hash1 == hash2, (
            "Hashing the same token must produce the same hash"
        )

    @given(st.data())
    @settings(max_examples=30)
    def test_different_tokens_produce_different_hashes(self, data):
        """For any two different tokens, their hashes are different."""
        token1 = generate_refresh_token()
        token2 = generate_refresh_token()
        # Extremely unlikely to collide but let's be safe
        assume(token1 != token2)
        hash1 = hash_refresh_token(token1)
        hash2 = hash_refresh_token(token2)
        assert hash1 != hash2, (
            "Different tokens must produce different hashes"
        )


# --- Property 6: Deactivated user authentication rejection ---


class TestDeactivatedUserRejection:
    """**Validates: Requirements 3.10**

    Property 6: Inactive users are rejected.
    For any user whose is_active field is false, all authentication
    attempts SHALL be rejected and all existing refresh tokens for
    that user SHALL be invalidated.
    """

    @given(user_id=user_id_strategy, role=role_strategy, password=password_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_deactivated_user_login_rejected(
        self, user_id: uuid.UUID, role: UserRole, password: str
    ):
        """For any deactivated user, login attempts are rejected."""
        user_repo = AsyncMock()
        refresh_token_repo = AsyncMock()
        login_attempt_repo = AsyncMock()

        hashed_pw = hash_password(password)

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "deactivated@example.com"
        mock_user.password_hash = hashed_pw
        mock_user.role = role
        mock_user.is_active = False  # Deactivated

        user_repo.get_by_email.return_value = mock_user
        refresh_token_repo.revoke_all_for_user.return_value = None

        service = AuthService(user_repo, refresh_token_repo, login_attempt_repo)

        with pytest.raises(UnauthorizedException):
            await service.login("deactivated@example.com", password)

        # Verify all tokens were invalidated
        refresh_token_repo.revoke_all_for_user.assert_called_once_with(user_id)

    @given(user_id=user_id_strategy, role=role_strategy)
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_deactivated_user_refresh_rejected(
        self, user_id: uuid.UUID, role: UserRole
    ):
        """For any deactivated user, refresh token usage is rejected."""
        user_repo = AsyncMock()
        refresh_token_repo = AsyncMock()
        login_attempt_repo = AsyncMock()

        token = generate_refresh_token()
        token_hash = hash_refresh_token(token)
        token_family = generate_token_family()

        mock_stored_token = MagicMock()
        mock_stored_token.id = uuid.uuid4()
        mock_stored_token.user_id = user_id
        mock_stored_token.token_hash = token_hash
        mock_stored_token.token_family = token_family
        mock_stored_token.is_revoked = False
        mock_stored_token.expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.role = role
        mock_user.is_active = False  # Deactivated

        refresh_token_repo.get_by_token_hash.return_value = mock_stored_token
        user_repo.get_by_id.return_value = mock_user
        refresh_token_repo.revoke_all_for_user.return_value = None

        service = AuthService(user_repo, refresh_token_repo, login_attempt_repo)

        with pytest.raises(UnauthorizedException):
            await service.refresh(token)

        # Verify all tokens for user were invalidated
        refresh_token_repo.revoke_all_for_user.assert_called_once_with(user_id)


# --- Property 7: Account lockout after consecutive failures ---


class TestAccountLockout:
    """**Validates: Requirements 3.11**

    Property 7: 5 failures in 15min triggers lockout.
    For any user account, if 5 consecutive failed login attempts occur
    within a 15-minute window, subsequent login attempts SHALL be
    rejected for 15 minutes regardless of credential validity.
    """

    @given(user_id=user_id_strategy, role=role_strategy, password=password_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_lockout_after_5_failures(
        self, user_id: uuid.UUID, role: UserRole, password: str
    ):
        """After 5 failed attempts in 15 minutes, login is locked."""
        user_repo = AsyncMock()
        refresh_token_repo = AsyncMock()
        login_attempt_repo = AsyncMock()

        hashed_pw = hash_password(password)

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "locked@example.com"
        mock_user.password_hash = hashed_pw
        mock_user.role = role
        mock_user.is_active = True

        user_repo.get_by_email.return_value = mock_user

        # Simulate 5 recent failures
        now = datetime.now(timezone.utc)
        mock_failures = [
            MagicMock(attempted_at=now - timedelta(minutes=i))
            for i in range(5)
        ]
        login_attempt_repo.get_recent_failures.return_value = mock_failures

        service = AuthService(user_repo, refresh_token_repo, login_attempt_repo)

        # Even with correct password, should be locked
        with pytest.raises(AccountLockedException):
            await service.login("locked@example.com", password)

    @given(
        user_id=user_id_strategy,
        role=role_strategy,
        password=password_strategy,
        num_failures=st.integers(min_value=0, max_value=4),
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_no_lockout_under_threshold(
        self, user_id: uuid.UUID, role: UserRole, password: str, num_failures: int
    ):
        """With fewer than 5 failures, login proceeds normally."""
        user_repo = AsyncMock()
        refresh_token_repo = AsyncMock()
        login_attempt_repo = AsyncMock()

        hashed_pw = hash_password(password)

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "user@example.com"
        mock_user.password_hash = hashed_pw
        mock_user.role = role
        mock_user.is_active = True

        user_repo.get_by_email.return_value = mock_user

        # Simulate fewer than 5 failures
        now = datetime.now(timezone.utc)
        mock_failures = [
            MagicMock(attempted_at=now - timedelta(minutes=i))
            for i in range(num_failures)
        ]
        login_attempt_repo.get_recent_failures.return_value = mock_failures
        login_attempt_repo.create.return_value = MagicMock()
        refresh_token_repo.create.return_value = MagicMock()

        service = AuthService(user_repo, refresh_token_repo, login_attempt_repo)

        # Should succeed with correct password
        result = await service.login("user@example.com", password)
        assert isinstance(result, TokenPair)
        assert result.access_token is not None
        assert result.refresh_token is not None


# --- Property 10: Invalid credentials return generic error ---


class TestGenericErrorOnInvalidCredentials:
    """**Validates: Requirements 3.2**

    Property 10: Same error for wrong email vs wrong password.
    For any login attempt with incorrect email, incorrect password, or
    both incorrect, the error response SHALL be identical in structure
    and message content, never revealing which specific field was wrong.
    """

    @given(password=password_strategy)
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_wrong_email_returns_generic_error(self, password: str):
        """When email doesn't exist, error message is generic."""
        user_repo = AsyncMock()
        refresh_token_repo = AsyncMock()
        login_attempt_repo = AsyncMock()

        # User not found
        user_repo.get_by_email.return_value = None

        service = AuthService(user_repo, refresh_token_repo, login_attempt_repo)

        with pytest.raises(UnauthorizedException) as exc_info:
            await service.login("nonexistent@example.com", password)

        assert "Invalid email or password" in exc_info.value.message

    @given(
        user_id=user_id_strategy,
        role=role_strategy,
        correct_password=password_strategy,
        wrong_password=password_strategy,
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_wrong_password_returns_same_generic_error(
        self,
        user_id: uuid.UUID,
        role: UserRole,
        correct_password: str,
        wrong_password: str,
    ):
        """When password is wrong, error message is identical to wrong email."""
        assume(correct_password != wrong_password)

        user_repo = AsyncMock()
        refresh_token_repo = AsyncMock()
        login_attempt_repo = AsyncMock()

        hashed_pw = hash_password(correct_password)

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "user@example.com"
        mock_user.password_hash = hashed_pw
        mock_user.role = role
        mock_user.is_active = True

        user_repo.get_by_email.return_value = mock_user
        login_attempt_repo.get_recent_failures.return_value = []
        login_attempt_repo.create.return_value = MagicMock()

        service = AuthService(user_repo, refresh_token_repo, login_attempt_repo)

        with pytest.raises(UnauthorizedException) as exc_info:
            await service.login("user@example.com", wrong_password)

        assert "Invalid email or password" in exc_info.value.message

    @given(
        user_id=user_id_strategy,
        role=role_strategy,
        correct_password=password_strategy,
        wrong_password=password_strategy,
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_error_messages_are_identical(
        self,
        user_id: uuid.UUID,
        role: UserRole,
        correct_password: str,
        wrong_password: str,
    ):
        """The error message for wrong email and wrong password are identical."""
        assume(correct_password != wrong_password)

        # Test wrong email scenario
        user_repo_1 = AsyncMock()
        refresh_token_repo_1 = AsyncMock()
        login_attempt_repo_1 = AsyncMock()
        user_repo_1.get_by_email.return_value = None

        service_1 = AuthService(user_repo_1, refresh_token_repo_1, login_attempt_repo_1)

        with pytest.raises(UnauthorizedException) as exc_wrong_email:
            await service_1.login("nonexistent@example.com", wrong_password)

        # Test wrong password scenario
        user_repo_2 = AsyncMock()
        refresh_token_repo_2 = AsyncMock()
        login_attempt_repo_2 = AsyncMock()

        hashed_pw = hash_password(correct_password)
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "user@example.com"
        mock_user.password_hash = hashed_pw
        mock_user.role = role
        mock_user.is_active = True

        user_repo_2.get_by_email.return_value = mock_user
        login_attempt_repo_2.get_recent_failures.return_value = []
        login_attempt_repo_2.create.return_value = MagicMock()

        service_2 = AuthService(user_repo_2, refresh_token_repo_2, login_attempt_repo_2)

        with pytest.raises(UnauthorizedException) as exc_wrong_pw:
            await service_2.login("user@example.com", wrong_password)

        # Error messages must be identical
        assert exc_wrong_email.value.message == exc_wrong_pw.value.message
        # Status codes must be identical
        assert exc_wrong_email.value.status_code == exc_wrong_pw.value.status_code

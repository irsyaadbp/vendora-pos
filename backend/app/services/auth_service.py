"""Authentication service handling login, token refresh, and logout.

Implements credential verification with account lockout protection,
refresh token rotation with family-based invalidation for reuse detection,
and deactivated user rejection.
"""

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.exceptions import AccountLockedException, UnauthorizedException
from app.domain.interfaces import (
    LoginAttemptRepositoryInterface,
    RefreshTokenRepositoryInterface,
    UserRepositoryInterface,
)
from app.infrastructure.security import (
    create_access_token,
    generate_refresh_token,
    generate_token_family,
    hash_refresh_token,
    verify_password,
)


@dataclass
class TokenPair:
    """Represents an access token and refresh token pair."""

    access_token: str
    refresh_token: str


class AuthService:
    """Service for authentication operations.

    Handles login with lockout protection, refresh token rotation
    with reuse detection, and logout with token invalidation.
    """

    def __init__(
        self,
        user_repo: UserRepositoryInterface,
        refresh_token_repo: RefreshTokenRepositoryInterface,
        login_attempt_repo: LoginAttemptRepositoryInterface,
    ) -> None:
        """Initialize AuthService with required repository dependencies.

        Args:
            user_repo: Repository for user data access.
            refresh_token_repo: Repository for refresh token management.
            login_attempt_repo: Repository for login attempt tracking.
        """
        self._user_repo = user_repo
        self._refresh_token_repo = refresh_token_repo
        self._login_attempt_repo = login_attempt_repo

    async def login(self, email: str, password: str) -> TokenPair:
        """Authenticate a user and return a token pair.

        Verifies credentials, checks account lockout status, generates
        access and refresh tokens, and stores the hashed refresh token
        with a new token family.

        Args:
            email: The user's email address.
            password: The user's plaintext password.

        Returns:
            A TokenPair containing access and refresh tokens.

        Raises:
            UnauthorizedException: If credentials are invalid or user is deactivated.
            AccountLockedException: If the account is locked due to too many failed attempts.
        """
        settings = get_settings()

        # Look up user by email
        user = await self._user_repo.get_by_email(email)

        if user is None:
            # Return generic error — don't reveal whether email exists
            raise UnauthorizedException(message="Invalid email or password")

        # Check if user account is deactivated
        if not user.is_active:
            # Invalidate all refresh tokens for deactivated user
            await self._refresh_token_repo.revoke_all_for_user(user.id)
            raise UnauthorizedException(message="Invalid email or password")

        # Check account lockout
        lockout_window = datetime.utcnow() - timedelta(
            minutes=settings.LOGIN_LOCKOUT_MINUTES
        )
        recent_failures = await self._login_attempt_repo.get_recent_failures(
            user_id=user.id,
            since=lockout_window,
        )

        if len(recent_failures) >= settings.MAX_LOGIN_ATTEMPTS:
            raise AccountLockedException()

        # Verify password
        if not verify_password(password, user.password_hash):
            # Record failed attempt
            await self._login_attempt_repo.create(
                user_id=user.id,
                success=False,
            )
            raise UnauthorizedException(message="Invalid email or password")

        # Record successful attempt
        await self._login_attempt_repo.create(
            user_id=user.id,
            success=True,
        )

        # Generate token pair
        access_token = create_access_token(
            user_id=str(user.id),
            role=user.role.value,
        )

        refresh_token = generate_refresh_token()
        token_family = generate_token_family()
        token_hash = hash_refresh_token(refresh_token)

        # Store hashed refresh token with family
        expires_at = datetime.utcnow() + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self._refresh_token_repo.create(
            user_id=user.id,
            token_hash=token_hash,
            token_family=token_family,
            expires_at=expires_at,
        )

        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    async def refresh(self, refresh_token_str: str) -> TokenPair:
        """Rotate a refresh token and issue a new token pair.

        Validates the refresh token, checks it hasn't been revoked or expired,
        verifies the user is still active, then rotates the token (revokes old,
        creates new with same family). Detects token reuse by checking if the
        token is already revoked, and invalidates the entire family if so.

        Args:
            refresh_token_str: The plaintext refresh token string.

        Returns:
            A new TokenPair with rotated tokens.

        Raises:
            UnauthorizedException: If the token is invalid, expired, revoked,
                or belongs to a deactivated user.
        """
        settings = get_settings()

        # Hash the incoming token to look it up
        token_hash = hash_refresh_token(refresh_token_str)
        stored_token = await self._refresh_token_repo.get_by_token_hash(token_hash)

        if stored_token is None:
            raise UnauthorizedException(message="Invalid refresh token")

        # Detect token reuse: if already revoked, invalidate entire family
        if stored_token.is_revoked:
            await self._refresh_token_repo.revoke_family(stored_token.token_family)
            raise UnauthorizedException(message="Invalid refresh token")

        # Check expiration
        now = datetime.utcnow()
        expires_at = stored_token.expires_at
        if now > expires_at:
            # Expired token — invalidate the family
            await self._refresh_token_repo.revoke_family(stored_token.token_family)
            raise UnauthorizedException(message="Invalid refresh token")

        # Check user is still active
        user = await self._user_repo.get_by_id(stored_token.user_id)
        if user is None or not user.is_active:
            # Deactivated user — invalidate all their tokens
            await self._refresh_token_repo.revoke_all_for_user(stored_token.user_id)
            raise UnauthorizedException(message="Invalid refresh token")

        # Rotate: revoke old token, issue new one with same family
        await self._refresh_token_repo.revoke(stored_token.id)

        # Generate new token pair
        access_token = create_access_token(
            user_id=str(user.id),
            role=user.role.value,
        )

        new_refresh_token = generate_refresh_token()
        new_token_hash = hash_refresh_token(new_refresh_token)

        expires_at_new = datetime.utcnow() + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self._refresh_token_repo.create(
            user_id=user.id,
            token_hash=new_token_hash,
            token_family=stored_token.token_family,
            expires_at=expires_at_new,
        )

        return TokenPair(access_token=access_token, refresh_token=new_refresh_token)

    async def logout(self, refresh_token_str: str) -> None:
        """Invalidate the current refresh token.

        Args:
            refresh_token_str: The plaintext refresh token string to invalidate.
        """
        token_hash = hash_refresh_token(refresh_token_str)
        stored_token = await self._refresh_token_repo.get_by_token_hash(token_hash)

        if stored_token is not None:
            await self._refresh_token_repo.revoke(stored_token.id)

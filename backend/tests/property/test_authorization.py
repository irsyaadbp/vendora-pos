"""Property-based tests for authorization.

Feature: vendora-pos-foundation
Property 8: JWT validation correctness
Property 9: RBAC enforcement

Validates: Requirements 4.1, 4.2, 4.3, 4.5, 4.6

These tests verify JWT token validation and role-based access control
using property-based testing with Hypothesis strategies. Tests exercise
the security module (verify_access_token) and the dependencies module
(get_current_user, require_admin) to ensure correct authorization behavior.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from jose import jwt as jose_jwt

# Set environment variables before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-property-tests-minimum-length")

from app.core.config import get_settings
from app.core.dependencies import get_current_user, require_admin
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.infrastructure.security import create_access_token, verify_access_token
from app.models.user import User
from app.schemas.enums import UserRole


# --- Strategies ---

user_id_strategy = st.uuids()

role_strategy = st.sampled_from([UserRole.admin, UserRole.staff])

expires_minutes_strategy = st.integers(min_value=1, max_value=1440)


# --- Property 8: JWT validation correctness ---


class TestJWTValidationCorrectness:
    """**Validates: Requirements 4.1, 4.2, 4.3**

    Property 8: Token accepted iff valid signature, not expired, valid structure, active user.
    For any JWT access token presented to a protected endpoint, the system SHALL
    accept the request if and only if the token has a valid signature, is not expired,
    has valid structure, and belongs to an active user.
    """

    @given(user_id=user_id_strategy, role=role_strategy)
    @settings(max_examples=50)
    def test_valid_token_accepted(self, user_id: uuid.UUID, role: UserRole):
        """For any valid JWT with correct signature, non-expired, and valid structure,
        verify_access_token returns the payload successfully."""
        token = create_access_token(
            user_id=str(user_id),
            role=role.value,
            expires_minutes=15,
        )

        payload = verify_access_token(token)

        assert payload["sub"] == str(user_id)
        assert payload["role"] == role.value
        assert "exp" in payload
        assert "iat" in payload

    @given(user_id=user_id_strategy, role=role_strategy)
    @settings(max_examples=50)
    def test_wrong_signature_rejected(self, user_id: uuid.UUID, role: UserRole):
        """For any JWT signed with a wrong secret, verify_access_token raises ValueError."""
        # Create token with a different secret
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "role": role.value,
            "exp": now + timedelta(minutes=15),
            "iat": now,
        }
        token = jose_jwt.encode(payload, "wrong-secret-key", algorithm="HS256")

        with pytest.raises(ValueError, match="Invalid token"):
            verify_access_token(token)

    @given(user_id=user_id_strategy, role=role_strategy)
    @settings(max_examples=50)
    def test_expired_token_rejected(self, user_id: uuid.UUID, role: UserRole):
        """For any expired JWT, verify_access_token raises ValueError."""
        settings_obj = get_settings()
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "role": role.value,
            "exp": now - timedelta(minutes=1),  # Already expired
            "iat": now - timedelta(minutes=16),
        }
        token = jose_jwt.encode(payload, settings_obj.JWT_SECRET, algorithm="HS256")

        with pytest.raises(ValueError, match="Invalid token"):
            verify_access_token(token)

    @given(user_id=user_id_strategy)
    @settings(max_examples=50)
    def test_missing_role_claim_rejected(self, user_id: uuid.UUID):
        """For any JWT missing the 'role' claim, verify_access_token raises ValueError."""
        settings_obj = get_settings()
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            # "role" is missing
            "exp": now + timedelta(minutes=15),
            "iat": now,
        }
        token = jose_jwt.encode(payload, settings_obj.JWT_SECRET, algorithm="HS256")

        with pytest.raises(ValueError, match="missing required claims"):
            verify_access_token(token)

    @given(role=role_strategy)
    @settings(max_examples=50)
    def test_missing_sub_claim_rejected(self, role: UserRole):
        """For any JWT missing the 'sub' claim, verify_access_token raises ValueError."""
        settings_obj = get_settings()
        now = datetime.now(timezone.utc)
        payload = {
            # "sub" is missing
            "role": role.value,
            "exp": now + timedelta(minutes=15),
            "iat": now,
        }
        token = jose_jwt.encode(payload, settings_obj.JWT_SECRET, algorithm="HS256")

        with pytest.raises(ValueError, match="missing required claims"):
            verify_access_token(token)

    @given(user_id=user_id_strategy, role=role_strategy)
    @settings(max_examples=30, deadline=None)
    @pytest.mark.asyncio
    async def test_active_user_with_valid_token_grants_access(
        self, user_id: uuid.UUID, role: UserRole
    ):
        """For any valid JWT belonging to an active user, get_current_user returns the user."""
        token = create_access_token(
            user_id=str(user_id),
            role=role.value,
            expires_minutes=15,
        )

        # Mock the database session and user repository
        mock_session = AsyncMock()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.role = role
        mock_user.is_active = True

        with patch(
            "app.repositories.user_repository.UserRepository"
        ) as MockUserRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_id.return_value = mock_user
            MockUserRepo.return_value = mock_repo_instance

            result = await get_current_user(token=token, session=mock_session)

        assert result == mock_user

    @given(user_id=user_id_strategy, role=role_strategy)
    @settings(max_examples=30, deadline=None)
    @pytest.mark.asyncio
    async def test_inactive_user_with_valid_token_rejected(
        self, user_id: uuid.UUID, role: UserRole
    ):
        """For any valid JWT belonging to an inactive user, get_current_user raises 401."""
        token = create_access_token(
            user_id=str(user_id),
            role=role.value,
            expires_minutes=15,
        )

        mock_session = AsyncMock()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.role = role
        mock_user.is_active = False  # Inactive user

        with patch(
            "app.repositories.user_repository.UserRepository"
        ) as MockUserRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_id.return_value = mock_user
            MockUserRepo.return_value = mock_repo_instance

            with pytest.raises(UnauthorizedException):
                await get_current_user(token=token, session=mock_session)

    @given(user_id=user_id_strategy, role=role_strategy)
    @settings(max_examples=30, deadline=None)
    @pytest.mark.asyncio
    async def test_expired_token_rejected_at_dependency_level(
        self, user_id: uuid.UUID, role: UserRole
    ):
        """For any expired JWT, get_current_user raises UnauthorizedException."""
        settings_obj = get_settings()
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "role": role.value,
            "exp": now - timedelta(minutes=1),
            "iat": now - timedelta(minutes=16),
        }
        token = jose_jwt.encode(payload, settings_obj.JWT_SECRET, algorithm="HS256")

        mock_session = AsyncMock()

        with pytest.raises(UnauthorizedException):
            await get_current_user(token=token, session=mock_session)


# --- Property 9: RBAC enforcement ---


class TestRBACEnforcement:
    """**Validates: Requirements 4.5, 4.6**

    Property 9: Access granted iff user role is in endpoint's allowed roles.
    For any authenticated user with a given role and any protected endpoint
    with defined role requirements, the system SHALL grant access if and only
    if the user's role is in the endpoint's allowed roles set.
    """

    @given(user_id=user_id_strategy)
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_admin_user_passes_require_admin(self, user_id: uuid.UUID):
        """For any admin user accessing any endpoint, access is granted via require_admin."""
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.role = UserRole.admin
        mock_user.is_active = True

        result = await require_admin(current_user=mock_user)

        assert result == mock_user

    @given(user_id=user_id_strategy)
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_staff_user_rejected_by_require_admin(self, user_id: uuid.UUID):
        """For any staff user accessing admin-only endpoint, access is denied with 403."""
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.role = UserRole.staff
        mock_user.is_active = True

        with pytest.raises(ForbiddenException):
            await require_admin(current_user=mock_user)

    @given(user_id=user_id_strategy, role=role_strategy)
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_any_authenticated_user_passes_get_current_user(
        self, user_id: uuid.UUID, role: UserRole
    ):
        """For any staff user accessing staff-allowed endpoint (get_current_user only),
        access is granted regardless of role."""
        token = create_access_token(
            user_id=str(user_id),
            role=role.value,
            expires_minutes=15,
        )

        mock_session = AsyncMock()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.role = role
        mock_user.is_active = True

        with patch(
            "app.repositories.user_repository.UserRepository"
        ) as MockUserRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_id.return_value = mock_user
            MockUserRepo.return_value = mock_repo_instance

            result = await get_current_user(token=token, session=mock_session)

        assert result == mock_user

    @given(user_id=user_id_strategy)
    @settings(max_examples=30, deadline=None)
    @pytest.mark.asyncio
    async def test_admin_role_grants_access_to_all_protected_endpoints(
        self, user_id: uuid.UUID
    ):
        """For any admin user, both get_current_user and require_admin succeed."""
        token = create_access_token(
            user_id=str(user_id),
            role=UserRole.admin.value,
            expires_minutes=15,
        )

        mock_session = AsyncMock()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.role = UserRole.admin
        mock_user.is_active = True

        with patch(
            "app.repositories.user_repository.UserRepository"
        ) as MockUserRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_id.return_value = mock_user
            MockUserRepo.return_value = mock_repo_instance

            # get_current_user should succeed
            user = await get_current_user(token=token, session=mock_session)
            assert user == mock_user

            # require_admin should also succeed
            admin_user = await require_admin(current_user=user)
            assert admin_user == mock_user

    @given(user_id=user_id_strategy)
    @settings(max_examples=30, deadline=None)
    @pytest.mark.asyncio
    async def test_staff_role_passes_authentication_but_fails_admin_authorization(
        self, user_id: uuid.UUID
    ):
        """For any staff user, get_current_user succeeds but require_admin raises 403."""
        token = create_access_token(
            user_id=str(user_id),
            role=UserRole.staff.value,
            expires_minutes=15,
        )

        mock_session = AsyncMock()
        mock_user = MagicMock(spec=User)
        mock_user.id = user_id
        mock_user.role = UserRole.staff
        mock_user.is_active = True

        with patch(
            "app.repositories.user_repository.UserRepository"
        ) as MockUserRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_id.return_value = mock_user
            MockUserRepo.return_value = mock_repo_instance

            # get_current_user should succeed (staff can access staff-allowed endpoints)
            user = await get_current_user(token=token, session=mock_session)
            assert user == mock_user

            # require_admin should fail (staff cannot access admin-only endpoints)
            with pytest.raises(ForbiddenException, match="Admin access required"):
                await require_admin(current_user=user)

    @given(user_id=user_id_strategy, role=role_strategy)
    @settings(max_examples=30, deadline=None)
    @pytest.mark.asyncio
    async def test_nonexistent_user_in_token_rejected(
        self, user_id: uuid.UUID, role: UserRole
    ):
        """For any JWT referencing a user that doesn't exist, get_current_user raises 401."""
        token = create_access_token(
            user_id=str(user_id),
            role=role.value,
            expires_minutes=15,
        )

        mock_session = AsyncMock()

        with patch(
            "app.repositories.user_repository.UserRepository"
        ) as MockUserRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_id.return_value = None  # User not found
            MockUserRepo.return_value = mock_repo_instance

            with pytest.raises(UnauthorizedException):
                await get_current_user(token=token, session=mock_session)

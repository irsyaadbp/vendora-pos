"""Unit tests for the security infrastructure module."""

import time
from unittest.mock import patch

import pytest

from app.infrastructure.security import (
    create_access_token,
    generate_refresh_token,
    generate_token_family,
    hash_password,
    hash_refresh_token,
    verify_access_token,
    verify_password,
)


# --- Password Hashing Tests ---


class TestPasswordHashing:
    """Tests for bcrypt password hashing functions."""

    def test_hash_password_returns_bcrypt_hash(self):
        """Hashed password should be a valid bcrypt hash."""
        password = "securepassword123"
        hashed = hash_password(password)
        # bcrypt hashes start with $2b$ (or $2a$/$2y$)
        assert hashed.startswith("$2b$")

    def test_hash_password_uses_cost_factor_12(self):
        """Hashed password should use cost factor 12."""
        password = "testpassword"
        hashed = hash_password(password)
        # bcrypt format: $2b$12$...
        assert "$2b$12$" in hashed

    def test_hash_password_different_hashes_for_same_password(self):
        """Same password should produce different hashes (due to salt)."""
        password = "samepassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_hash_password_does_not_contain_plaintext(self):
        """Hash should not contain the plaintext password."""
        password = "mysecretpassword"
        hashed = hash_password(password)
        assert password not in hashed

    def test_verify_password_correct(self):
        """Correct password should verify successfully."""
        password = "correctpassword"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Incorrect password should fail verification."""
        password = "correctpassword"
        hashed = hash_password(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty_string(self):
        """Empty string should not match a non-empty password hash."""
        password = "notempty"
        hashed = hash_password(password)
        assert verify_password("", hashed) is False


# --- JWT Access Token Tests ---


class TestJWTAccessToken:
    """Tests for JWT access token creation and verification."""

    @patch("app.infrastructure.security.get_settings")
    def test_create_access_token_returns_string(self, mock_settings):
        """Created token should be a non-empty string."""
        mock_settings.return_value.JWT_SECRET = "test-secret-key"
        mock_settings.return_value.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15

        token = create_access_token(user_id="user-123", role="admin")
        assert isinstance(token, str)
        assert len(token) > 0

    @patch("app.infrastructure.security.get_settings")
    def test_create_and_verify_access_token(self, mock_settings):
        """Token should be verifiable and contain correct claims."""
        mock_settings.return_value.JWT_SECRET = "test-secret-key"
        mock_settings.return_value.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15

        token = create_access_token(user_id="user-456", role="staff")
        payload = verify_access_token(token)

        assert payload["sub"] == "user-456"
        assert payload["role"] == "staff"
        assert "exp" in payload
        assert "iat" in payload

    @patch("app.infrastructure.security.get_settings")
    def test_create_access_token_custom_expiry(self, mock_settings):
        """Token should respect custom expiry parameter."""
        mock_settings.return_value.JWT_SECRET = "test-secret-key"
        mock_settings.return_value.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15

        token = create_access_token(
            user_id="user-789", role="admin", expires_minutes=30
        )
        payload = verify_access_token(token)

        # Verify expiry is approximately 30 minutes from now
        exp = payload["exp"]
        iat = payload["iat"]
        diff = exp - iat
        assert diff == 30 * 60  # 30 minutes in seconds

    @patch("app.infrastructure.security.get_settings")
    def test_create_access_token_default_expiry(self, mock_settings):
        """Token should use config default expiry when not specified."""
        mock_settings.return_value.JWT_SECRET = "test-secret-key"
        mock_settings.return_value.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15

        token = create_access_token(user_id="user-abc", role="staff")
        payload = verify_access_token(token)

        exp = payload["exp"]
        iat = payload["iat"]
        diff = exp - iat
        assert diff == 15 * 60  # 15 minutes in seconds

    @patch("app.infrastructure.security.get_settings")
    def test_verify_access_token_invalid_token(self, mock_settings):
        """Invalid token should raise ValueError."""
        mock_settings.return_value.JWT_SECRET = "test-secret-key"

        with pytest.raises(ValueError, match="Invalid token"):
            verify_access_token("not-a-valid-token")

    @patch("app.infrastructure.security.get_settings")
    def test_verify_access_token_wrong_secret(self, mock_settings):
        """Token signed with different secret should fail verification."""
        mock_settings.return_value.JWT_SECRET = "secret-one"
        mock_settings.return_value.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15

        token = create_access_token(user_id="user-x", role="admin")

        # Change the secret for verification
        mock_settings.return_value.JWT_SECRET = "secret-two"

        with pytest.raises(ValueError, match="Invalid token"):
            verify_access_token(token)

    @patch("app.infrastructure.security.get_settings")
    def test_verify_access_token_expired(self, mock_settings):
        """Expired token should raise ValueError."""
        mock_settings.return_value.JWT_SECRET = "test-secret-key"
        mock_settings.return_value.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15

        # Create a token that expires immediately
        token = create_access_token(
            user_id="user-exp", role="staff", expires_minutes=0
        )

        # Wait a moment to ensure expiry
        time.sleep(1)

        with pytest.raises(ValueError, match="Invalid token"):
            verify_access_token(token)


# --- Refresh Token Tests ---


class TestRefreshToken:
    """Tests for refresh token generation and hashing."""

    def test_generate_refresh_token_returns_string(self):
        """Generated token should be a non-empty string."""
        token = generate_refresh_token()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_refresh_token_is_unique(self):
        """Each generated token should be unique."""
        tokens = {generate_refresh_token() for _ in range(100)}
        assert len(tokens) == 100

    def test_generate_refresh_token_sufficient_length(self):
        """Token should be sufficiently long for security (128 hex chars = 64 bytes)."""
        token = generate_refresh_token()
        assert len(token) == 128  # 64 bytes hex-encoded

    def test_hash_refresh_token_returns_sha256(self):
        """Hashed token should be a valid SHA-256 hex digest."""
        token = "test-refresh-token"
        hashed = hash_refresh_token(token)
        # SHA-256 produces 64 hex characters
        assert len(hashed) == 64
        assert all(c in "0123456789abcdef" for c in hashed)

    def test_hash_refresh_token_deterministic(self):
        """Same token should always produce the same hash."""
        token = "consistent-token"
        hash1 = hash_refresh_token(token)
        hash2 = hash_refresh_token(token)
        assert hash1 == hash2

    def test_hash_refresh_token_different_for_different_tokens(self):
        """Different tokens should produce different hashes."""
        hash1 = hash_refresh_token("token-one")
        hash2 = hash_refresh_token("token-two")
        assert hash1 != hash2

    def test_hash_refresh_token_not_equal_to_plaintext(self):
        """Hash should not equal the plaintext token."""
        token = "my-refresh-token"
        hashed = hash_refresh_token(token)
        assert hashed != token


# --- Token Family Tests ---


class TestTokenFamily:
    """Tests for token family ID generation."""

    def test_generate_token_family_returns_string(self):
        """Generated family ID should be a non-empty string."""
        family_id = generate_token_family()
        assert isinstance(family_id, str)
        assert len(family_id) > 0

    def test_generate_token_family_is_uuid_format(self):
        """Generated family ID should be a valid UUID."""
        import uuid

        family_id = generate_token_family()
        # Should not raise
        uuid.UUID(family_id)

    def test_generate_token_family_is_unique(self):
        """Each generated family ID should be unique."""
        families = {generate_token_family() for _ in range(100)}
        assert len(families) == 100

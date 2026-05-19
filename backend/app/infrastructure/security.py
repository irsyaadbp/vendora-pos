"""Security infrastructure for JWT tokens and password hashing.

Provides bcrypt password hashing (cost factor 12), JWT access token
generation/verification, and refresh token utilities with token family
tracking for rotation.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings


# --- Password Hashing ---


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with cost factor 12.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt hash string.
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        password: The plaintext password to verify.
        hashed: The bcrypt hash to verify against.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# --- JWT Access Tokens ---


def create_access_token(
    user_id: str, role: str, expires_minutes: int | None = None
) -> str:
    """Create a JWT access token with user claims.

    Args:
        user_id: The user's unique identifier.
        role: The user's role (e.g., 'admin', 'staff').
        expires_minutes: Optional custom expiry in minutes.
            Defaults to JWT_ACCESS_TOKEN_EXPIRE_MINUTES from config.

    Returns:
        The encoded JWT token string.
    """
    settings = get_settings()
    if expires_minutes is None:
        expires_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)

    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "iat": now,
    }

    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def verify_access_token(token: str) -> dict:
    """Decode and verify a JWT access token.

    Args:
        token: The JWT token string to verify.

    Returns:
        The decoded token payload as a dictionary with 'sub', 'role', 'exp' claims.

    Raises:
        ValueError: If the token is invalid, expired, or has missing claims.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e

    if "sub" not in payload or "role" not in payload:
        raise ValueError("Invalid token: missing required claims")

    return payload


# --- Refresh Tokens ---


def generate_refresh_token() -> str:
    """Generate a cryptographically secure random refresh token.

    Returns:
        A URL-safe random string (64 bytes, hex-encoded).
    """
    return secrets.token_hex(64)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token using SHA-256 for secure storage.

    Args:
        token: The plaintext refresh token.

    Returns:
        The SHA-256 hex digest of the token.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --- Token Family ---


def generate_token_family() -> str:
    """Generate a unique token family ID for refresh token rotation tracking.

    Token families group related refresh tokens together so that if a
    compromised token is detected, all tokens in the family can be
    invalidated.

    Returns:
        A unique string identifier for the token family.
    """
    return str(uuid.uuid4())

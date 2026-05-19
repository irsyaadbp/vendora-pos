"""Application exception hierarchy for consistent error handling.

All custom exceptions inherit from AppException and carry:
- A human-readable message
- An HTTP status code
- Optional field-level errors for validation failures

Exception handlers in main.py convert these into the standard
APIErrorResponse format, ensuring internal details are never leaked.
"""

from typing import Optional

from app.schemas.common import FieldError


class AppException(Exception):
    """Base application exception.

    All domain-specific exceptions should inherit from this class.
    """

    status_code: int = 500
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        errors: Optional[list[FieldError]] = None,
    ) -> None:
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.errors: list[FieldError] = errors or []
        super().__init__(self.message)


class NotFoundException(AppException):
    """Raised when a requested resource does not exist."""

    status_code: int = 404
    message: str = "Resource not found"


class ConflictException(AppException):
    """Raised when a request conflicts with existing state (e.g. duplicate)."""

    status_code: int = 409
    message: str = "Resource already exists"


class UnauthorizedException(AppException):
    """Raised when authentication is missing or invalid."""

    status_code: int = 401
    message: str = "Authentication required"


class ForbiddenException(AppException):
    """Raised when the user lacks permission for the requested action."""

    status_code: int = 403
    message: str = "Insufficient permissions"


class ValidationException(AppException):
    """Raised when request data fails business-level validation."""

    status_code: int = 422
    message: str = "Validation failed"

    def __init__(
        self,
        message: Optional[str] = None,
        errors: Optional[list[FieldError]] = None,
    ) -> None:
        super().__init__(message=message, errors=errors)


class RateLimitException(AppException):
    """Raised when a client exceeds the allowed request rate."""

    status_code: int = 429
    message: str = "Rate limit exceeded. Please try again later"


class AccountLockedException(AppException):
    """Raised when a user account is temporarily locked due to failed attempts."""

    status_code: int = 423
    message: str = "Account temporarily locked due to too many failed attempts"

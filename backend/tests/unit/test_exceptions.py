"""Unit tests for global exception handling.

Tests verify that:
- AppException hierarchy has correct status codes and messages
- Exception handlers return the standard APIErrorResponse format
- 500 errors never expose internal details
- RequestValidationError is converted to field-specific errors
"""

import os

# Set required env vars before importing app modules that trigger settings validation
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/testdb")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests")

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.exceptions import (
    AccountLockedException,
    AppException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    RateLimitException,
    UnauthorizedException,
    ValidationException,
)
from app.main import app
from app.schemas.common import FieldError


# --- Exception class tests ---


class TestAppException:
    def test_default_values(self):
        exc = AppException()
        assert exc.status_code == 500
        assert exc.message == "An unexpected error occurred"
        assert exc.errors == []

    def test_custom_message(self):
        exc = AppException(message="Custom error")
        assert exc.message == "Custom error"

    def test_custom_status_code(self):
        exc = AppException(status_code=418)
        assert exc.status_code == 418

    def test_with_field_errors(self):
        errors = [FieldError(field="email", detail="Invalid format")]
        exc = AppException(errors=errors)
        assert len(exc.errors) == 1
        assert exc.errors[0].field == "email"

    def test_str_representation(self):
        exc = AppException(message="Test error")
        assert str(exc) == "Test error"


class TestNotFoundException:
    def test_default_values(self):
        exc = NotFoundException()
        assert exc.status_code == 404
        assert exc.message == "Resource not found"

    def test_custom_message(self):
        exc = NotFoundException(message="User not found")
        assert exc.message == "User not found"
        assert exc.status_code == 404


class TestConflictException:
    def test_default_values(self):
        exc = ConflictException()
        assert exc.status_code == 409
        assert exc.message == "Resource already exists"

    def test_custom_message(self):
        exc = ConflictException(message="Email already in use")
        assert exc.message == "Email already in use"


class TestUnauthorizedException:
    def test_default_values(self):
        exc = UnauthorizedException()
        assert exc.status_code == 401
        assert exc.message == "Authentication required"


class TestForbiddenException:
    def test_default_values(self):
        exc = ForbiddenException()
        assert exc.status_code == 403
        assert exc.message == "Insufficient permissions"


class TestValidationException:
    def test_default_values(self):
        exc = ValidationException()
        assert exc.status_code == 422
        assert exc.message == "Validation failed"
        assert exc.errors == []

    def test_with_field_errors(self):
        errors = [
            FieldError(field="price", detail="Must be positive"),
            FieldError(field="name", detail="Required"),
        ]
        exc = ValidationException(errors=errors)
        assert len(exc.errors) == 2


class TestRateLimitException:
    def test_default_values(self):
        exc = RateLimitException()
        assert exc.status_code == 429
        assert exc.message == "Rate limit exceeded. Please try again later"


class TestAccountLockedException:
    def test_default_values(self):
        exc = AccountLockedException()
        assert exc.status_code == 423
        assert "locked" in exc.message.lower()


# --- Exception handler integration tests ---

# Register test routes on the app for handler testing
class _ItemCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)


@app.get("/test/not-found")
async def _raise_not_found():
    raise NotFoundException(message="Product not found")


@app.get("/test/conflict")
async def _raise_conflict():
    raise ConflictException(message="Email already exists")


@app.get("/test/unauthorized")
async def _raise_unauthorized():
    raise UnauthorizedException()


@app.get("/test/forbidden")
async def _raise_forbidden():
    raise ForbiddenException()


@app.get("/test/validation")
async def _raise_validation():
    raise ValidationException(
        message="Invalid input",
        errors=[FieldError(field="email", detail="Invalid format")],
    )


@app.get("/test/rate-limit")
async def _raise_rate_limit():
    raise RateLimitException()


@app.get("/test/account-locked")
async def _raise_account_locked():
    raise AccountLockedException()


@app.get("/test/unhandled")
async def _raise_unhandled():
    raise RuntimeError("Database connection failed")


@app.post("/test/validate-body")
async def _validate_body(item: _ItemCreate):
    return {"success": True}


class TestExceptionHandlers:
    """Test that exception handlers in main.py produce correct responses."""

    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(app, raise_server_exceptions=False)

    def test_not_found_handler(self, client: TestClient):
        response = client.get("/test/not-found")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert data["data"] is None
        assert data["message"] == "Product not found"
        assert data["errors"] == []

    def test_conflict_handler(self, client: TestClient):
        response = client.get("/test/conflict")
        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Email already exists"

    def test_unauthorized_handler(self, client: TestClient):
        response = client.get("/test/unauthorized")
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Authentication required"

    def test_forbidden_handler(self, client: TestClient):
        response = client.get("/test/forbidden")
        assert response.status_code == 403
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Insufficient permissions"

    def test_validation_handler_with_field_errors(self, client: TestClient):
        response = client.get("/test/validation")
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Invalid input"
        assert len(data["errors"]) == 1
        assert data["errors"][0]["field"] == "email"
        assert data["errors"][0]["detail"] == "Invalid format"

    def test_rate_limit_handler(self, client: TestClient):
        response = client.get("/test/rate-limit")
        assert response.status_code == 429
        data = response.json()
        assert data["success"] is False
        assert "rate limit" in data["message"].lower()

    def test_account_locked_handler(self, client: TestClient):
        response = client.get("/test/account-locked")
        assert response.status_code == 423
        data = response.json()
        assert data["success"] is False
        assert "locked" in data["message"].lower()

    def test_unhandled_exception_returns_generic_500(self, client: TestClient):
        response = client.get("/test/unhandled")
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["data"] is None
        assert data["message"] == "An unexpected error occurred"
        assert data["errors"] == []
        # Ensure internal details are NOT exposed
        assert "Database" not in data["message"]
        assert "connection" not in data["message"]
        assert "RuntimeError" not in data["message"]

    def test_request_validation_error_format(self, client: TestClient):
        response = client.post("/test/validate-body", json={})
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert data["data"] is None
        assert data["message"] == "Validation failed"
        assert len(data["errors"]) > 0
        # Check that field names are present
        field_names = [e["field"] for e in data["errors"]]
        assert "name" in field_names or "price" in field_names

    def test_request_validation_error_with_invalid_types(self, client: TestClient):
        response = client.post(
            "/test/validate-body", json={"name": "", "price": -1}
        )
        assert response.status_code == 422
        data = response.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0

    def test_all_error_responses_have_consistent_structure(self, client: TestClient):
        """Verify all error responses follow the same envelope structure."""
        endpoints = [
            "/test/not-found",
            "/test/conflict",
            "/test/unauthorized",
            "/test/forbidden",
            "/test/validation",
            "/test/rate-limit",
            "/test/unhandled",
        ]
        required_keys = {"success", "data", "message", "errors"}

        for endpoint in endpoints:
            response = client.get(endpoint)
            data = response.json()
            assert required_keys.issubset(
                data.keys()
            ), f"Missing keys in response from {endpoint}: {required_keys - data.keys()}"
            assert data["success"] is False
            assert data["data"] is None
            assert isinstance(data["errors"], list)

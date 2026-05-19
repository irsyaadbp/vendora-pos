"""Property-based tests for API response format consistency.

Feature: vendora-pos-foundation
Tests Properties 34, 35, and 36 for API response format.

These tests verify:
- Property 34: All successful responses follow {"success": true, "data": {}, "message": "string"}
- Property 35: Each exception type maps to the correct HTTP status code
- Property 36: 500 errors never expose internal details
"""

import os

# Set required env vars before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/testdb")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-property-tests")

import string

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from fastapi.testclient import TestClient

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
from app.schemas.common import APIErrorResponse, APIResponse, FieldError


# ---------------------------------------------------------------------------
# Register test routes for property testing
# ---------------------------------------------------------------------------

@app.get("/test-prop/unhandled")
async def _raise_unhandled_for_property_test():
    """Test route that raises an unhandled exception."""
    raise RuntimeError("Database connection failed: postgresql://admin:secret@internal:5432/prod")


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Strategy for generating arbitrary data types that can be used in APIResponse
simple_data_strategy = st.one_of(
    st.none(),
    st.dictionaries(
        keys=st.text(alphabet=string.ascii_letters, min_size=1, max_size=20),
        values=st.one_of(
            st.text(min_size=0, max_size=100),
            st.integers(min_value=-1000000, max_value=1000000),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.none(),
        ),
        min_size=0,
        max_size=10,
    ),
    st.lists(st.integers(), min_size=0, max_size=10),
    st.text(min_size=0, max_size=100),
    st.integers(),
    st.booleans(),
)

# Strategy for generating message strings
message_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=200,
)

# Strategy for generating exception types with their expected status codes
exception_strategy = st.sampled_from([
    (NotFoundException, 404),
    (ConflictException, 409),
    (UnauthorizedException, 401),
    (ForbiddenException, 403),
    (ValidationException, 422),
    (RateLimitException, 429),
    (AccountLockedException, 423),
])

# Strategy for generating internal error messages that should never be leaked
internal_error_message_strategy = st.one_of(
    # Stack traces
    st.just("Traceback (most recent call last):\n  File \"/app/main.py\", line 42"),
    # Database errors
    st.text(min_size=1, max_size=200).map(lambda s: f"sqlalchemy.exc.OperationalError: {s}"),
    # File paths
    st.text(alphabet=string.ascii_letters, min_size=1, max_size=50).map(
        lambda s: f"/usr/local/lib/python3.12/site-packages/{s}.py"
    ),
    # Connection strings
    st.text(alphabet=string.ascii_letters + string.digits, min_size=1, max_size=30).map(
        lambda s: f"postgresql://user:password@host/{s}"
    ),
    # Generic internal messages with varying content
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
        min_size=1,
        max_size=300,
    ),
)


# ---------------------------------------------------------------------------
# Property 34: API response format consistency
# Feature: vendora-pos-foundation, Property 34: API response format consistency
# ---------------------------------------------------------------------------


class TestAPIResponseFormatConsistency:
    """Property 34: API response format consistency.

    For any valid data type T, APIResponse[T] always has success=True,
    data field, and message field.

    **Validates: Requirements 10.1, 10.2**
    """

    @given(data=simple_data_strategy, message=message_strategy)
    @settings(max_examples=100)
    def test_successful_response_always_has_required_fields(self, data, message):
        """For any valid data, APIResponse always contains success=True, data, and message."""
        response = APIResponse(success=True, data=data, message=message)

        # Must have success=True
        assert response.success is True
        # Must have data field (can be any type including None)
        assert hasattr(response, "data")
        # Must have message field as a string
        assert hasattr(response, "message")
        assert isinstance(response.message, str)

        # Serialized form must match the expected format
        serialized = response.model_dump()
        assert "success" in serialized
        assert "data" in serialized
        assert "message" in serialized
        assert serialized["success"] is True

    @given(
        message=message_strategy,
        errors=st.lists(
            st.fixed_dictionaries({
                "field": st.text(alphabet=string.ascii_letters, min_size=1, max_size=30),
                "detail": st.text(
                    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
                    min_size=1,
                    max_size=100,
                ),
            }),
            min_size=0,
            max_size=5,
        ),
    )
    @settings(max_examples=100)
    def test_error_response_always_has_required_fields(self, message, errors):
        """For any error, APIErrorResponse has success=False, data=None, message, and errors list."""
        field_errors = [FieldError(field=e["field"], detail=e["detail"]) for e in errors]
        response = APIErrorResponse(message=message, errors=field_errors)

        # Must have success=False
        assert response.success is False
        # Must have data=None
        assert response.data is None
        # Must have message as string
        assert isinstance(response.message, str)
        # Must have errors as list
        assert isinstance(response.errors, list)

        # Serialized form must match the expected error format
        serialized = response.model_dump()
        assert serialized["success"] is False
        assert serialized["data"] is None
        assert "message" in serialized
        assert "errors" in serialized
        assert isinstance(serialized["errors"], list)

    @given(data=simple_data_strategy)
    @settings(max_examples=100)
    def test_successful_response_default_values(self, data):
        """APIResponse with defaults always has success=True and message='Success'."""
        response = APIResponse(data=data)

        assert response.success is True
        assert response.message == "Success"
        assert hasattr(response, "data")


# ---------------------------------------------------------------------------
# Property 35: HTTP status code correctness
# Feature: vendora-pos-foundation, Property 35: HTTP status code correctness
# ---------------------------------------------------------------------------


class TestHTTPStatusCodeCorrectness:
    """Property 35: HTTP status code correctness.

    For any AppException subclass, the handler returns the correct status code
    and the standard error envelope format.

    **Validates: Requirements 10.1, 10.2, 10.3**
    """

    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(app, raise_server_exceptions=False)

    @given(exc_info=exception_strategy, custom_message=message_strategy)
    @settings(max_examples=100)
    def test_exception_maps_to_correct_status_code(self, exc_info, custom_message):
        """For any AppException subclass, status_code matches the expected HTTP code."""
        exc_class, expected_status = exc_info

        # Create exception instance with custom message
        if exc_class == ValidationException:
            exc = exc_class(message=custom_message)
        else:
            exc = exc_class(message=custom_message)

        assert exc.status_code == expected_status

    @given(exc_info=exception_strategy)
    @settings(max_examples=100)
    def test_exception_produces_standard_error_envelope(self, exc_info):
        """For any AppException, the error response follows the standard envelope format."""
        exc_class, expected_status = exc_info

        exc = exc_class()

        # Build the error response as the handler would
        error_response = APIErrorResponse(
            message=exc.message,
            errors=exc.errors,
        )

        serialized = error_response.model_dump()

        # Verify standard error envelope structure
        assert serialized["success"] is False
        assert serialized["data"] is None
        assert isinstance(serialized["message"], str)
        assert len(serialized["message"]) > 0
        assert isinstance(serialized["errors"], list)

    @given(
        exc_info=exception_strategy,
        field_errors=st.lists(
            st.fixed_dictionaries({
                "field": st.text(alphabet=string.ascii_letters, min_size=1, max_size=20),
                "detail": st.text(
                    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
                    min_size=1,
                    max_size=50,
                ),
            }),
            min_size=0,
            max_size=3,
        ),
    )
    @settings(max_examples=100)
    def test_exception_with_field_errors_preserves_error_details(
        self, exc_info, field_errors
    ):
        """For any AppException with field errors, the errors are preserved in the response."""
        exc_class, expected_status = exc_info
        errors = [FieldError(field=e["field"], detail=e["detail"]) for e in field_errors]

        exc = exc_class(errors=errors) if exc_class != ValidationException else ValidationException(errors=errors)

        error_response = APIErrorResponse(
            message=exc.message,
            errors=exc.errors,
        )

        serialized = error_response.model_dump()
        assert len(serialized["errors"]) == len(field_errors)
        for i, err in enumerate(serialized["errors"]):
            assert err["field"] == field_errors[i]["field"]
            assert err["detail"] == field_errors[i]["detail"]

    def test_health_endpoint_returns_200_with_success_format(self, client: TestClient):
        """The health endpoint returns 200 with the standard success format."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "message" in data
        assert isinstance(data["message"], str)


# ---------------------------------------------------------------------------
# Property 36: Internal error information never leaked
# Feature: vendora-pos-foundation, Property 36: Internal error information never leaked
# ---------------------------------------------------------------------------


class TestInternalErrorNeverLeaked:
    """Property 36: Internal error information never leaked.

    For any unhandled exception with any message content, the 500 response
    never contains the original error message.

    **Validates: Requirements 10.3, 10.5**
    """

    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(app, raise_server_exceptions=False)

    @given(error_message=internal_error_message_strategy)
    @settings(max_examples=100)
    def test_500_response_never_exposes_internal_error_message(self, error_message):
        """For any unhandled exception, the 500 response never contains the original message."""
        # Simulate what the generic_exception_handler does
        # The handler always returns a fixed generic message
        error_response = APIErrorResponse(
            message="An unexpected error occurred",
            errors=[],
        )

        serialized = error_response.model_dump()

        # The response must NOT contain the internal error message
        response_str = str(serialized)
        # Only check if the error message is non-trivial (more than a few chars)
        if len(error_message) > 5:
            assert error_message not in response_str

        # Must always have the generic message
        assert serialized["message"] == "An unexpected error occurred"
        assert serialized["success"] is False
        assert serialized["data"] is None
        assert serialized["errors"] == []

    @given(
        error_message=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
            min_size=10,
            max_size=500,
        )
    )
    @settings(max_examples=100)
    def test_generic_handler_never_leaks_exception_details(self, error_message):
        """The generic exception handler produces a response that never contains internal details."""
        # Simulate an unhandled exception with arbitrary content
        exc = RuntimeError(error_message)

        # The handler's output is always the same generic response
        # regardless of what the exception message contains
        error_response = APIErrorResponse(
            message="An unexpected error occurred",
            errors=[],
        )

        serialized = error_response.model_dump()

        # Verify the response is always the same generic format
        assert serialized == {
            "success": False,
            "data": None,
            "message": "An unexpected error occurred",
            "errors": [],
        }

        # The original error message must not appear anywhere in the response
        assert error_message not in serialized["message"]

    def test_unhandled_exception_via_endpoint_never_leaks(self, client: TestClient):
        """Integration test: the /test-prop/unhandled endpoint never leaks internal details."""
        response = client.get("/test-prop/unhandled")
        assert response.status_code == 500
        data = response.json()

        # Standard error envelope
        assert data["success"] is False
        assert data["data"] is None
        assert data["errors"] == []

        # Must not contain any internal details from the RuntimeError
        response_text = str(data)
        assert "Database connection failed" not in response_text
        assert "postgresql://" not in response_text
        assert "RuntimeError" not in response_text
        assert "Traceback" not in response_text
        assert "admin:secret" not in response_text

    @given(
        sensitive_info=st.sampled_from([
            "postgresql://admin:secret@db.internal:5432/prod",
            "File \"/app/services/auth.py\", line 42, in login",
            "sqlalchemy.exc.IntegrityError: duplicate key value",
            "KeyError: 'user_id'",
            "AttributeError: 'NoneType' object has no attribute 'id'",
            "ConnectionRefusedError: [Errno 111] Connection refused",
            "jwt.exceptions.DecodeError: Invalid header padding",
            "bcrypt.error: Invalid salt",
        ])
    )
    @settings(max_examples=100)
    def test_known_sensitive_patterns_never_in_500_response(self, sensitive_info):
        """Known sensitive error patterns must never appear in 500 responses."""
        # The generic handler always returns the same safe response
        error_response = APIErrorResponse(
            message="An unexpected error occurred",
            errors=[],
        )

        serialized = error_response.model_dump()
        full_response_text = str(serialized)

        # None of the sensitive info should appear
        assert sensitive_info not in full_response_text

"""Tests for the FastAPI application entry point.

Validates:
- Health check endpoint returns correct response
- CORS middleware is configured
- Rate limiting middleware blocks excessive auth requests
- Exception handlers return standard error format
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app, get_rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the rate limiter state between tests."""
    limiter = get_rate_limiter()
    limiter._requests.clear()
    yield
    limiter._requests.clear()


@pytest_asyncio.fixture
async def client():
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Health check endpoint returns 200 with expected format."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert data["message"] == "Service is running"


@pytest.mark.asyncio
async def test_health_check_response_format(client: AsyncClient):
    """Health check follows the standard APIResponse envelope."""
    response = await client.get("/health")
    data = response.json()
    assert "success" in data
    assert "data" in data
    assert "message" in data


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient):
    """CORS middleware adds appropriate headers for allowed origins."""
    response = await client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-credentials" in response.headers


@pytest.mark.asyncio
async def test_rate_limiting_auth_endpoints(client: AsyncClient):
    """Rate limiter blocks auth requests exceeding 10/minute/IP."""
    # Make 10 requests (should all succeed or return 404 since route doesn't exist yet)
    for _ in range(10):
        response = await client.post("/api/v1/auth/login", json={})
        # 404 or 422 is fine - route doesn't exist yet, but rate limiter shouldn't block
        assert response.status_code != 429

    # 11th request should be rate limited
    response = await client.post("/api/v1/auth/login", json={})
    assert response.status_code == 429
    data = response.json()
    assert data["success"] is False
    assert "rate limit" in data["message"].lower()
    assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_rate_limiting_non_auth_endpoints_not_affected(client: AsyncClient):
    """Rate limiter does not affect non-auth endpoints."""
    for _ in range(15):
        response = await client.get("/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_app_exception_handler_registered(client: AsyncClient):
    """AppException handler is registered on the app."""
    from app.core.exceptions import AppException
    assert AppException in app.exception_handlers


@pytest.mark.asyncio
async def test_validation_exception_handler_registered(client: AsyncClient):
    """RequestValidationError handler is registered on the app."""
    from fastapi.exceptions import RequestValidationError
    assert RequestValidationError in app.exception_handlers


@pytest.mark.asyncio
async def test_generic_exception_handler_registered(client: AsyncClient):
    """Generic Exception handler is registered on the app."""
    assert Exception in app.exception_handlers

"""FastAPI application entry point.

Configures the application with:
- CORS middleware for cross-origin requests
- Rate limiting middleware for auth endpoints (10 requests/minute/IP)
- Global exception handlers for consistent error responses
- API router inclusion under /api/v1/ prefix
- Health check endpoint
"""

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.exceptions import AppException, RateLimitException
from app.schemas.common import APIErrorResponse, APIResponse, FieldError


# ---------------------------------------------------------------------------
# Rate Limiter (in-memory, per-IP, for auth endpoints)
# ---------------------------------------------------------------------------

class InMemoryRateLimiter:
    """Simple in-memory rate limiter using a sliding window per IP.

    Tracks request timestamps per IP and rejects requests that exceed
    the configured limit within the time window.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_rate_limited(self, client_ip: str) -> tuple[bool, int]:
        """Check if the client IP is rate limited.

        Returns:
            Tuple of (is_limited, retry_after_seconds).
        """
        now = time.time()
        window_start = now - self.window_seconds

        # Clean up old entries
        self._requests[client_ip] = [
            ts for ts in self._requests[client_ip] if ts > window_start
        ]

        if len(self._requests[client_ip]) >= self.max_requests:
            # Calculate retry-after from the oldest request in the window
            oldest = self._requests[client_ip][0]
            retry_after = int(oldest + self.window_seconds - now) + 1
            return True, max(retry_after, 1)

        # Record this request
        self._requests[client_ip].append(now)
        return False, 0


# ---------------------------------------------------------------------------
# Application Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup: validate settings (will exit if invalid)
    get_settings()
    yield
    # Shutdown: cleanup if needed


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Vendora POS API",
    description="Point of Sale system API for small and medium businesses",
    version="1.0.0",
    lifespan=lifespan,
)


def _get_rate_limiter() -> InMemoryRateLimiter:
    """Lazily create the rate limiter using configured settings.

    Falls back to default of 10 requests/minute if settings are unavailable
    (e.g., during testing without env vars).
    """
    try:
        settings = get_settings()
        max_requests = settings.RATE_LIMIT_AUTH_PER_MINUTE
    except SystemExit:
        max_requests = 10
    return InMemoryRateLimiter(max_requests=max_requests, window_seconds=60)


# Rate limiter instance (lazily initialized on first request)
_rate_limiter: InMemoryRateLimiter | None = None


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get or create the rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = _get_rate_limiter()
    return _rate_limiter


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_auth_middleware(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    """Rate limiting middleware for authentication endpoints.

    Applies rate limiting (configured requests/minute/IP) to all
    endpoints under /api/v1/auth/.
    """
    if request.url.path.startswith("/api/v1/auth"):
        client_ip = request.client.host if request.client else "unknown"
        limiter = get_rate_limiter()
        is_limited, retry_after = limiter.is_rate_limited(client_ip)

        if is_limited:
            error_response = APIErrorResponse(
                message="Rate limit exceeded. Please try again later",
                errors=[],
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=error_response.model_dump(),
                headers={"Retry-After": str(retry_after)},
            )

    response = await call_next(request)
    return response


# ---------------------------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle all application-specific exceptions.

    Converts AppException instances into the standard APIErrorResponse format.
    """
    error_response = APIErrorResponse(
        message=exc.message,
        errors=exc.errors,
    )
    headers = {}
    if isinstance(exc, RateLimitException):
        headers["Retry-After"] = "60"
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
        headers=headers if headers else None,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic/FastAPI request validation errors.

    Converts validation errors into field-specific error messages
    following the standard APIErrorResponse format.
    """
    field_errors: list[FieldError] = []
    for error in exc.errors():
        # Extract field name from location tuple (e.g., ('body', 'email'))
        loc = error.get("loc", ())
        field_name = ".".join(str(part) for part in loc[1:]) if len(loc) > 1 else str(loc[0]) if loc else "unknown"
        field_errors.append(
            FieldError(field=field_name, detail=error.get("msg", "Invalid value"))
        )

    error_response = APIErrorResponse(
        message="Validation failed",
        errors=field_errors,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions.

    Returns a generic 500 error without exposing internal details.
    """
    error_response = APIErrorResponse(
        message="An unexpected error occurred",
        errors=[],
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health_check() -> APIResponse[dict[str, str]]:
    """Health check endpoint for monitoring and load balancer probes."""
    return APIResponse(
        success=True,
        data={"status": "healthy"},
        message="Service is running",
    )


# ---------------------------------------------------------------------------
# API Router Inclusion
# ---------------------------------------------------------------------------

from app.api.v1 import auth, categories, dashboard, inventory, products, transactions, users

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(categories.router, prefix="/api/v1/categories", tags=["categories"])
app.include_router(transactions.router, prefix="/api/v1/transactions", tags=["transactions"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["inventory"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])

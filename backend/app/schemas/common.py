"""Common API response schemas for consistent response formatting.

All API responses follow a standardized envelope format:
- Success: {"success": true, "data": {}, "message": "string"}
- Error: {"success": false, "data": null, "message": "string", "errors": []}
- Paginated: includes meta with total_count, page, page_size, total_pages
"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class FieldError(BaseModel):
    """Represents a single field-level validation error."""

    field: str = Field(description="The name of the field that failed validation")
    detail: str = Field(description="Human-readable description of the validation failure")


class APIResponse(BaseModel, Generic[T]):
    """Standard successful API response envelope.

    Used for all non-paginated successful responses.
    """

    success: bool = True
    data: Optional[T] = None
    message: str = "Success"


class APIErrorResponse(BaseModel):
    """Standard error API response envelope.

    Used for all error responses including validation, auth, and server errors.
    """

    success: bool = False
    data: None = None
    message: str
    errors: list[FieldError] = Field(default_factory=list)


class PaginatedMeta(BaseModel):
    """Pagination metadata included in paginated responses."""

    total_count: int = Field(ge=0, description="Total number of records matching the query")
    page: int = Field(ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(ge=1, le=100, description="Number of records per page")
    total_pages: int = Field(ge=0, description="Total number of pages available")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated API response envelope.

    Used for all list endpoints that support pagination.
    """

    success: bool = True
    data: list[T] = Field(default_factory=list)
    message: str = "Success"
    meta: PaginatedMeta

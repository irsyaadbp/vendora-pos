"""Product management API routes.

Provides CRUD operations for products:
- GET / : List products with pagination (any authenticated user)
- GET /search : Search products with query and filters (any authenticated user)
- POST / : Create a new product (admin only)
- GET /{product_id} : Get a single product by ID (any authenticated user)
- PUT /{product_id} : Update a product (admin only)
- DELETE /{product_id} : Soft delete a product (admin only)
"""

import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    PaginationParams,
    get_current_user,
    get_pagination,
    require_admin,
)
from app.domain.interfaces import ProductFilters as DomainProductFilters
from app.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.common import APIResponse, PaginatedMeta, PaginatedResponse
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter()

# Default low stock threshold (matches config default)
_LOW_STOCK_THRESHOLD = 10


async def _get_db_session():  # type: ignore[no-untyped-def]
    """Lazy wrapper for get_db_session to avoid circular imports at module level."""
    from app.infrastructure.database import get_db_session

    async for session in get_db_session():
        yield session


def _get_product_service(session: AsyncSession) -> ProductService:
    """Construct a ProductService with required repository dependencies.

    Args:
        session: The async database session for the current request.

    Returns:
        A fully-initialized ProductService instance.
    """
    product_repo = ProductRepository(session)
    category_repo = CategoryRepository(session)
    return ProductService(product_repo=product_repo, category_repo=category_repo)


def _get_low_stock_threshold() -> int:
    """Get the low stock threshold from settings, with fallback."""
    try:
        from app.core.config import get_settings

        settings = get_settings()
        return settings.LOW_STOCK_THRESHOLD
    except SystemExit:
        return _LOW_STOCK_THRESHOLD


def _to_product_response(product) -> ProductResponse:  # type: ignore[no-untyped-def]
    """Convert a Product model instance to a ProductResponse schema.

    Computes the low_stock field based on the configured threshold.

    Args:
        product: The SQLAlchemy Product model instance.

    Returns:
        ProductResponse schema with computed low_stock field.
    """
    threshold = _get_low_stock_threshold()
    return ProductResponse(
        id=product.id,
        name=product.name,
        sku=product.sku,
        barcode=product.barcode,
        price=product.price,
        stock=product.stock,
        category_id=product.category_id,
        is_active=product.is_active,
        low_stock=product.stock <= threshold,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


@router.get("/", response_model=PaginatedResponse[ProductResponse])
async def list_products(
    pagination: PaginationParams = Depends(get_pagination),
    _current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(_get_db_session),
) -> PaginatedResponse[ProductResponse]:
    """List products with pagination.

    Authenticated (any role). Returns only active products by default.
    Results are sorted by created_at descending.
    """
    product_service = _get_product_service(session)
    filters = DomainProductFilters()
    result = await product_service.search_products(
        query=None, filters=filters, pagination=pagination
    )

    product_responses = [_to_product_response(p) for p in result.items]
    total_pages = (
        math.ceil(result.total_count / pagination.page_size)
        if result.total_count > 0
        else 0
    )

    return PaginatedResponse(
        success=True,
        data=product_responses,
        message="Products retrieved successfully",
        meta=PaginatedMeta(
            total_count=result.total_count,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        ),
    )


@router.get("/search", response_model=PaginatedResponse[ProductResponse])
async def search_products(
    q: Optional[str] = Query(None, description="Search query (partial name, exact SKU or barcode)"),
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category ID"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    _current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(_get_db_session),
) -> PaginatedResponse[ProductResponse]:
    """Search products with query string and filters.

    Authenticated (any role). Supports partial name matching and exact
    SKU/barcode matching. Returns only active products by default.
    """
    product_service = _get_product_service(session)
    pagination = PaginationParams(page=page, page_size=page_size)
    filters = DomainProductFilters(category_id=category_id)
    result = await product_service.search_products(
        query=q, filters=filters, pagination=pagination
    )

    product_responses = [_to_product_response(p) for p in result.items]
    total_pages = (
        math.ceil(result.total_count / pagination.page_size)
        if result.total_count > 0
        else 0
    )

    return PaginatedResponse(
        success=True,
        data=product_responses,
        message="Products retrieved successfully",
        meta=PaginatedMeta(
            total_count=result.total_count,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        ),
    )


@router.post("/", response_model=APIResponse[ProductResponse], status_code=201)
async def create_product(
    body: ProductCreate,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[ProductResponse]:
    """Create a new product.

    Requires admin role. Validates SKU and barcode uniqueness.
    Returns the created product.
    """
    product_service = _get_product_service(session)
    product = await product_service.create_product(
        name=body.name,
        sku=body.sku,
        price=body.price,
        stock=body.stock,
        barcode=body.barcode,
        category_id=body.category_id,
    )
    await session.commit()

    return APIResponse(
        success=True,
        data=_to_product_response(product),
        message="Product created successfully",
    )


@router.get("/{product_id}", response_model=APIResponse[ProductResponse])
async def get_product(
    product_id: uuid.UUID,
    _current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[ProductResponse]:
    """Get a single product by ID.

    Authenticated (any role). Returns 404 if product does not exist.
    """
    from app.core.exceptions import NotFoundException

    product_repo = ProductRepository(session)
    product = await product_repo.get_by_id(product_id)

    if product is None:
        raise NotFoundException(message="Product not found")

    return APIResponse(
        success=True,
        data=_to_product_response(product),
        message="Product retrieved successfully",
    )


@router.put("/{product_id}", response_model=APIResponse[ProductResponse])
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[ProductResponse]:
    """Update an existing product.

    Requires admin role. Only provided fields will be updated.
    Returns 404 if product does not exist, 409 for duplicate SKU/barcode.
    """
    product_service = _get_product_service(session)
    product = await product_service.update_product(
        product_id=product_id,
        name=body.name,
        sku=body.sku,
        barcode=body.barcode,
        price=body.price,
        stock=body.stock,
        category_id=body.category_id,
        is_active=body.is_active,
    )
    await session.commit()

    return APIResponse(
        success=True,
        data=_to_product_response(product),
        message="Product updated successfully",
    )


@router.delete("/{product_id}", response_model=APIResponse[ProductResponse])
async def delete_product(
    product_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[ProductResponse]:
    """Soft delete a product (sets is_active to false).

    Requires admin role. Returns 404 if product does not exist.
    """
    product_service = _get_product_service(session)
    product = await product_service.soft_delete_product(product_id=product_id)
    await session.commit()

    return APIResponse(
        success=True,
        data=_to_product_response(product),
        message="Product deleted successfully",
    )

"""Inventory management API routes.

Provides stock management operations (all admin-only):
- POST /stock-in : Record a stock-in operation
- POST /stock-out : Record a stock-out operation
- POST /adjust : Adjust stock to an exact quantity
- GET /low-stock : List products below low-stock threshold
- GET /logs/{product_id} : Get inventory log history for a product
"""

import math
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    PaginationParams,
    get_pagination,
    require_admin,
)
from app.models.user import User
from app.repositories.inventory_log_repository import InventoryLogRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.common import APIResponse, PaginatedMeta, PaginatedResponse
from app.schemas.inventory import (
    InventoryLogResponse,
    StockAdjustmentRequest,
    StockOperationRequest,
)
from app.schemas.product import ProductResponse
from app.services.inventory_service import InventoryService

router = APIRouter()

# Default low stock threshold (matches config default)
_LOW_STOCK_THRESHOLD = 10


async def _get_db_session():  # type: ignore[no-untyped-def]
    """Lazy wrapper for get_db_session to avoid circular imports at module level."""
    from app.infrastructure.database import get_db_session

    async for session in get_db_session():
        yield session


def _get_inventory_service(session: AsyncSession) -> InventoryService:
    """Construct an InventoryService with required repository dependencies.

    Args:
        session: The async database session for the current request.

    Returns:
        A fully-initialized InventoryService instance.
    """
    product_repo = ProductRepository(session)
    log_repo = InventoryLogRepository(session)
    return InventoryService(product_repo=product_repo, log_repo=log_repo)


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


def _to_inventory_log_response(log) -> InventoryLogResponse:  # type: ignore[no-untyped-def]
    """Convert an InventoryLog model instance to an InventoryLogResponse schema.

    Args:
        log: The SQLAlchemy InventoryLog model instance.

    Returns:
        InventoryLogResponse schema.
    """
    return InventoryLogResponse(
        id=log.id,
        product_id=log.product_id,
        user_id=log.user_id,
        adjustment_type=log.adjustment_type,
        quantity_change=log.quantity_change,
        reason=log.reason,
        created_at=log.created_at,
    )


@router.post("/stock-in", response_model=APIResponse[ProductResponse], status_code=200)
async def stock_in(
    body: StockOperationRequest,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[ProductResponse]:
    """Record a stock-in operation, increasing product stock.

    Requires admin role. Returns the updated product with new stock level.
    Returns 404 if product does not exist, 422 for invalid quantity range.
    """
    inventory_service = _get_inventory_service(session)
    product = await inventory_service.stock_in(
        product_id=body.product_id,
        quantity=body.quantity,
        user_id=admin.id,
    )
    await session.commit()

    return APIResponse(
        success=True,
        data=_to_product_response(product),
        message="Stock-in recorded successfully",
    )


@router.post("/stock-out", response_model=APIResponse[ProductResponse], status_code=200)
async def stock_out(
    body: StockOperationRequest,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[ProductResponse]:
    """Record a stock-out operation, decreasing product stock.

    Requires admin role. Returns the updated product with new stock level.
    Returns 400 for insufficient stock, 404 if product does not exist,
    422 for invalid quantity range.
    """
    inventory_service = _get_inventory_service(session)
    product = await inventory_service.stock_out(
        product_id=body.product_id,
        quantity=body.quantity,
        user_id=admin.id,
    )
    await session.commit()

    return APIResponse(
        success=True,
        data=_to_product_response(product),
        message="Stock-out recorded successfully",
    )


@router.post("/adjust", response_model=APIResponse[ProductResponse], status_code=200)
async def adjust_stock(
    body: StockAdjustmentRequest,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[ProductResponse]:
    """Adjust product stock to an exact quantity with a mandatory reason.

    Requires admin role. Returns the updated product with new stock level.
    Returns 404 if product does not exist, 422 for invalid quantity or reason.
    """
    inventory_service = _get_inventory_service(session)
    product = await inventory_service.adjust_stock(
        product_id=body.product_id,
        new_quantity=body.new_quantity,
        reason=body.reason,
        user_id=admin.id,
    )
    await session.commit()

    return APIResponse(
        success=True,
        data=_to_product_response(product),
        message="Stock adjustment recorded successfully",
    )


@router.get("/low-stock", response_model=PaginatedResponse[ProductResponse])
async def get_low_stock_products(
    pagination: PaginationParams = Depends(get_pagination),
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> PaginatedResponse[ProductResponse]:
    """List products at or below the configured low-stock threshold.

    Requires admin role. Returns paginated results with default page size of 20.
    """
    inventory_service = _get_inventory_service(session)
    result = await inventory_service.get_low_stock_products(pagination=pagination)

    product_responses = [_to_product_response(p) for p in result.items]
    total_pages = (
        math.ceil(result.total_count / pagination.page_size)
        if result.total_count > 0
        else 0
    )

    return PaginatedResponse(
        success=True,
        data=product_responses,
        message="Low-stock products retrieved successfully",
        meta=PaginatedMeta(
            total_count=result.total_count,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        ),
    )


@router.get("/logs/{product_id}", response_model=PaginatedResponse[InventoryLogResponse])
async def get_product_inventory_logs(
    product_id: uuid.UUID,
    pagination: PaginationParams = Depends(get_pagination),
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> PaginatedResponse[InventoryLogResponse]:
    """Get paginated inventory log history for a specific product.

    Requires admin role. Results are sorted by timestamp descending (most recent first).
    Returns 404 if product does not exist.
    """
    inventory_service = _get_inventory_service(session)
    result = await inventory_service.get_product_logs(
        product_id=product_id, pagination=pagination
    )

    log_responses = [_to_inventory_log_response(log) for log in result.items]
    total_pages = (
        math.ceil(result.total_count / pagination.page_size)
        if result.total_count > 0
        else 0
    )

    return PaginatedResponse(
        success=True,
        data=log_responses,
        message="Inventory logs retrieved successfully",
        meta=PaginatedMeta(
            total_count=result.total_count,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        ),
    )

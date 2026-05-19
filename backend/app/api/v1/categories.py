"""Category management API routes.

Provides CRUD operations for categories:
- GET / : List categories with pagination (any authenticated user)
- POST / : Create a new category (admin only)
- PUT /{category_id} : Update a category (admin only)
- DELETE /{category_id} : Delete a category (admin only)
"""

import math
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    PaginationParams,
    get_current_user,
    get_pagination,
    require_admin,
)
from app.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.schemas.common import APIResponse, PaginatedMeta, PaginatedResponse
from app.services.product_service import ProductService

router = APIRouter()


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


def _to_category_response(category) -> CategoryResponse:  # type: ignore[no-untyped-def]
    """Convert a Category model instance to a CategoryResponse schema.

    Args:
        category: The SQLAlchemy Category model instance.

    Returns:
        CategoryResponse schema.
    """
    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        created_at=category.created_at,
    )


@router.get("/", response_model=PaginatedResponse[CategoryResponse])
async def list_categories(
    pagination: PaginationParams = Depends(get_pagination),
    _current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(_get_db_session),
) -> PaginatedResponse[CategoryResponse]:
    """List categories with pagination.

    Authenticated (any role). Results are sorted by name ascending.
    """
    product_service = _get_product_service(session)
    result = await product_service.list_categories(pagination=pagination)

    category_responses = [_to_category_response(c) for c in result.items]
    total_pages = (
        math.ceil(result.total_count / pagination.page_size)
        if result.total_count > 0
        else 0
    )

    return PaginatedResponse(
        success=True,
        data=category_responses,
        message="Categories retrieved successfully",
        meta=PaginatedMeta(
            total_count=result.total_count,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        ),
    )


@router.post("/", response_model=APIResponse[CategoryResponse], status_code=201)
async def create_category(
    body: CategoryCreate,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[CategoryResponse]:
    """Create a new category.

    Requires admin role. Validates name uniqueness.
    Returns the created category.
    """
    product_service = _get_product_service(session)
    category = await product_service.create_category(
        name=body.name,
        description=body.description,
    )
    await session.commit()

    return APIResponse(
        success=True,
        data=_to_category_response(category),
        message="Category created successfully",
    )


@router.put("/{category_id}", response_model=APIResponse[CategoryResponse])
async def update_category(
    category_id: uuid.UUID,
    body: CategoryUpdate,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[CategoryResponse]:
    """Update an existing category.

    Requires admin role. Only provided fields will be updated.
    Returns 404 if category does not exist, 409 for duplicate name.
    """
    product_service = _get_product_service(session)
    category = await product_service.update_category(
        category_id=category_id,
        name=body.name,
        description=body.description,
    )
    await session.commit()

    return APIResponse(
        success=True,
        data=_to_category_response(category),
        message="Category updated successfully",
    )


@router.delete("/{category_id}", response_model=APIResponse[None])
async def delete_category(
    category_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[None]:
    """Delete a category.

    Requires admin role. Returns 404 if category does not exist.
    """
    product_service = _get_product_service(session)
    await product_service.delete_category(category_id=category_id)
    await session.commit()

    return APIResponse(
        success=True,
        data=None,
        message="Category deleted successfully",
    )

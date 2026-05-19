"""Product and category management service.

Provides product CRUD with SKU/barcode uniqueness validation,
soft delete, paginated search, and category CRUD with unique
name validation. All operations enforce business rules and
raise domain exceptions for constraint violations.
"""

import uuid
from decimal import Decimal
from typing import Optional

from app.core.dependencies import PaginationParams
from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.domain.interfaces import (
    CategoryRepositoryInterface,
    PaginatedResult,
    ProductFilters,
    ProductRepositoryInterface,
)
from app.models.category import Category
from app.models.product import Product
from app.schemas.common import FieldError


class ProductService:
    """Service for product and category management operations.

    Handles product creation, updates, soft deletion, and paginated search
    with filtering. Also provides category CRUD operations. All operations
    enforce business rules including SKU/barcode uniqueness and field
    constraint validation.
    """

    def __init__(
        self,
        product_repo: ProductRepositoryInterface,
        category_repo: CategoryRepositoryInterface,
    ) -> None:
        """Initialize ProductService with required repository dependencies.

        Args:
            product_repo: Repository for product data access operations.
            category_repo: Repository for category data access operations.
        """
        self._product_repo = product_repo
        self._category_repo = category_repo

    async def create_product(
        self,
        name: str,
        sku: str,
        price: Decimal,
        stock: int,
        barcode: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
    ) -> Product:
        """Create a new product with validated uniqueness and field constraints.

        Args:
            name: Product name (1-255 characters).
            sku: Stock Keeping Unit (1-100 characters, must be unique).
            price: Product price (0.01 to 999,999,999.99).
            stock: Initial stock quantity (non-negative integer).
            barcode: Optional barcode (must be unique if provided).
            category_id: Optional category UUID.

        Returns:
            The created Product instance.

        Raises:
            ValidationException: If input validation fails.
            ConflictException: If SKU or barcode already exists.
            NotFoundException: If category_id references a non-existent category.
        """
        # Validate field constraints
        errors: list[FieldError] = []

        if not name or not name.strip():
            errors.append(
                FieldError(field="name", detail="Product name is required")
            )
        elif len(name) > 255:
            errors.append(
                FieldError(
                    field="name",
                    detail="Product name must be at most 255 characters",
                )
            )

        if not sku or not sku.strip():
            errors.append(
                FieldError(field="sku", detail="SKU is required")
            )
        elif len(sku) > 100:
            errors.append(
                FieldError(
                    field="sku",
                    detail="SKU must be at most 100 characters",
                )
            )

        if price < Decimal("0.01"):
            errors.append(
                FieldError(
                    field="price",
                    detail="Price must be at least 0.01",
                )
            )
        elif price > Decimal("999999999.99"):
            errors.append(
                FieldError(
                    field="price",
                    detail="Price must be at most 999,999,999.99",
                )
            )

        if stock < 0:
            errors.append(
                FieldError(
                    field="stock",
                    detail="Stock must be a non-negative integer",
                )
            )

        if errors:
            raise ValidationException(message="Validation failed", errors=errors)

        # Check SKU uniqueness
        existing_by_sku = await self._product_repo.get_by_sku(sku.strip())
        if existing_by_sku is not None:
            raise ConflictException(
                message="A product with this SKU already exists"
            )

        # Check barcode uniqueness if provided
        if barcode is not None and barcode.strip():
            existing_by_barcode = await self._product_repo.get_by_barcode(
                barcode.strip()
            )
            if existing_by_barcode is not None:
                raise ConflictException(
                    message="A product with this barcode already exists"
                )

        # Validate category exists if provided
        if category_id is not None:
            category = await self._category_repo.get_by_id(category_id)
            if category is None:
                raise NotFoundException(message="Category not found")

        # Create product
        product = await self._product_repo.create(
            name=name.strip(),
            sku=sku.strip(),
            price=price,
            stock=stock,
            barcode=barcode.strip() if barcode and barcode.strip() else None,
            category_id=category_id,
        )

        return product

    async def update_product(
        self,
        product_id: uuid.UUID,
        name: Optional[str] = None,
        sku: Optional[str] = None,
        barcode: Optional[str] = None,
        price: Optional[Decimal] = None,
        stock: Optional[int] = None,
        category_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
    ) -> Product:
        """Update provided fields for an existing product.

        Only fields that are explicitly passed (not None) will be updated.
        Re-validates uniqueness constraints when SKU or barcode changes.

        Args:
            product_id: The UUID of the product to update.
            name: New product name (optional, 1-255 characters).
            sku: New SKU (optional, 1-100 characters, must be unique).
            barcode: New barcode (optional, must be unique if provided).
            price: New price (optional, 0.01 to 999,999,999.99).
            stock: New stock quantity (optional, non-negative integer).
            category_id: New category UUID (optional).
            is_active: New active status (optional).

        Returns:
            The updated Product instance.

        Raises:
            NotFoundException: If the product does not exist.
            ValidationException: If input validation fails.
            ConflictException: If new SKU or barcode already exists.
        """
        # Check product exists
        existing_product = await self._product_repo.get_by_id(product_id)
        if existing_product is None:
            raise NotFoundException(message="Product not found")

        # Validate provided fields
        errors: list[FieldError] = []

        if name is not None:
            if not name.strip():
                errors.append(
                    FieldError(field="name", detail="Product name is required")
                )
            elif len(name) > 255:
                errors.append(
                    FieldError(
                        field="name",
                        detail="Product name must be at most 255 characters",
                    )
                )

        if sku is not None:
            if not sku.strip():
                errors.append(
                    FieldError(field="sku", detail="SKU is required")
                )
            elif len(sku) > 100:
                errors.append(
                    FieldError(
                        field="sku",
                        detail="SKU must be at most 100 characters",
                    )
                )

        if price is not None:
            if price < Decimal("0.01"):
                errors.append(
                    FieldError(
                        field="price",
                        detail="Price must be at least 0.01",
                    )
                )
            elif price > Decimal("999999999.99"):
                errors.append(
                    FieldError(
                        field="price",
                        detail="Price must be at most 999,999,999.99",
                    )
                )

        if stock is not None and stock < 0:
            errors.append(
                FieldError(
                    field="stock",
                    detail="Stock must be a non-negative integer",
                )
            )

        if errors:
            raise ValidationException(message="Validation failed", errors=errors)

        # Check SKU uniqueness if SKU is being changed
        if sku is not None and sku.strip() != existing_product.sku:
            existing_by_sku = await self._product_repo.get_by_sku(sku.strip())
            if existing_by_sku is not None:
                raise ConflictException(
                    message="A product with this SKU already exists"
                )

        # Check barcode uniqueness if barcode is being changed
        if barcode is not None:
            barcode_value = barcode.strip() if barcode.strip() else None
            if (
                barcode_value is not None
                and barcode_value != existing_product.barcode
            ):
                existing_by_barcode = await self._product_repo.get_by_barcode(
                    barcode_value
                )
                if existing_by_barcode is not None:
                    raise ConflictException(
                        message="A product with this barcode already exists"
                    )

        # Validate category exists if provided
        if category_id is not None:
            category = await self._category_repo.get_by_id(category_id)
            if category is None:
                raise NotFoundException(message="Category not found")

        # Build update kwargs with only provided fields
        update_kwargs: dict[str, object] = {}
        if name is not None:
            update_kwargs["name"] = name.strip()
        if sku is not None:
            update_kwargs["sku"] = sku.strip()
        if barcode is not None:
            update_kwargs["barcode"] = (
                barcode.strip() if barcode.strip() else None
            )
        if price is not None:
            update_kwargs["price"] = price
        if stock is not None:
            update_kwargs["stock"] = stock
        if category_id is not None:
            update_kwargs["category_id"] = category_id
        if is_active is not None:
            update_kwargs["is_active"] = is_active

        if not update_kwargs:
            return existing_product

        updated_product = await self._product_repo.update(
            product_id, **update_kwargs
        )
        if updated_product is None:
            raise NotFoundException(message="Product not found")

        return updated_product

    async def soft_delete_product(self, product_id: uuid.UUID) -> Product:
        """Soft delete a product by setting is_active to false.

        Args:
            product_id: The UUID of the product to soft delete.

        Returns:
            The updated Product instance with is_active set to false.

        Raises:
            NotFoundException: If the product does not exist.
        """
        existing_product = await self._product_repo.get_by_id(product_id)
        if existing_product is None:
            raise NotFoundException(message="Product not found")

        updated_product = await self._product_repo.update(
            product_id, is_active=False
        )
        if updated_product is None:
            raise NotFoundException(message="Product not found")

        return updated_product

    async def search_products(
        self,
        query: Optional[str],
        filters: ProductFilters,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """Search products with pagination, filtering, and text matching.

        Performs partial matching (ilike) on product name and exact matching
        on SKU and barcode. Only returns active products by default.

        Args:
            query: Search query string (partial name, exact SKU, or exact barcode).
            filters: Filtering criteria (category_id, is_active).
            pagination: Pagination parameters (page, page_size).

        Returns:
            PaginatedResult containing matching products and total count.
        """
        return await self._product_repo.search(
            query=query,
            filters=filters,
            pagination=pagination,
        )

    # ─── Category CRUD ───────────────────────────────────────────────────

    async def create_category(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> Category:
        """Create a new category with unique name validation.

        Args:
            name: Category name (1-100 characters, must be unique).
            description: Optional category description.

        Returns:
            The created Category instance.

        Raises:
            ValidationException: If name validation fails.
            ConflictException: If a category with this name already exists.
        """
        errors: list[FieldError] = []

        if not name or not name.strip():
            errors.append(
                FieldError(field="name", detail="Category name is required")
            )
        elif len(name) > 100:
            errors.append(
                FieldError(
                    field="name",
                    detail="Category name must be at most 100 characters",
                )
            )

        if errors:
            raise ValidationException(message="Validation failed", errors=errors)

        # Check name uniqueness
        existing = await self._category_repo.get_by_name(name.strip())
        if existing is not None:
            raise ConflictException(
                message="A category with this name already exists"
            )

        category = await self._category_repo.create(
            name=name.strip(),
            description=description,
        )

        return category

    async def list_categories(
        self,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """List categories with pagination.

        Args:
            pagination: Pagination parameters (page, page_size).

        Returns:
            PaginatedResult containing categories and total count.
        """
        return await self._category_repo.list(pagination=pagination)

    async def update_category(
        self,
        category_id: uuid.UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Category:
        """Update a category's fields.

        Args:
            category_id: The UUID of the category to update.
            name: New category name (optional, 1-100 characters, must be unique).
            description: New description (optional).

        Returns:
            The updated Category instance.

        Raises:
            NotFoundException: If the category does not exist.
            ValidationException: If name validation fails.
            ConflictException: If the new name already exists.
        """
        existing_category = await self._category_repo.get_by_id(category_id)
        if existing_category is None:
            raise NotFoundException(message="Category not found")

        errors: list[FieldError] = []

        if name is not None:
            if not name.strip():
                errors.append(
                    FieldError(
                        field="name", detail="Category name is required"
                    )
                )
            elif len(name) > 100:
                errors.append(
                    FieldError(
                        field="name",
                        detail="Category name must be at most 100 characters",
                    )
                )

        if errors:
            raise ValidationException(message="Validation failed", errors=errors)

        # Check name uniqueness if name is being changed
        if name is not None and name.strip() != existing_category.name:
            existing_by_name = await self._category_repo.get_by_name(
                name.strip()
            )
            if existing_by_name is not None:
                raise ConflictException(
                    message="A category with this name already exists"
                )

        # Build update kwargs with only provided fields
        update_kwargs: dict[str, object] = {}
        if name is not None:
            update_kwargs["name"] = name.strip()
        if description is not None:
            update_kwargs["description"] = description

        if not update_kwargs:
            return existing_category

        updated_category = await self._category_repo.update(
            category_id, **update_kwargs
        )
        if updated_category is None:
            raise NotFoundException(message="Category not found")

        return updated_category

    async def delete_category(self, category_id: uuid.UUID) -> None:
        """Delete a category.

        Args:
            category_id: The UUID of the category to delete.

        Raises:
            NotFoundException: If the category does not exist.
        """
        existing_category = await self._category_repo.get_by_id(category_id)
        if existing_category is None:
            raise NotFoundException(message="Category not found")

        await self._category_repo.delete(category_id)

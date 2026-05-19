"""SQLAlchemy implementation of ProductRepositoryInterface.

Provides async database operations for product management using
SQLAlchemy's async session, including search with partial name matching
and exact SKU/barcode matching.
"""

import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import PaginationParams
from app.domain.interfaces import PaginatedResult, ProductFilters, ProductRepositoryInterface
from app.models.product import Product


class ProductRepository(ProductRepositoryInterface):
    """Concrete implementation of ProductRepositoryInterface using SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations.
        """
        self._session = session

    async def create(
        self,
        name: str,
        sku: str,
        price: object,
        stock: int,
        barcode: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
    ) -> Product:
        """Create a new product record in the database."""
        product = Product(
            name=name,
            sku=sku,
            price=price,
            stock=stock,
            barcode=barcode,
            category_id=category_id,
        )
        self._session.add(product)
        await self._session.flush()
        await self._session.refresh(product)
        return product

    async def get_by_id(self, product_id: uuid.UUID) -> Optional[Product]:
        """Retrieve a product by its UUID."""
        stmt = select(Product).where(Product.id == product_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Retrieve a product by its SKU."""
        stmt = select(Product).where(Product.sku == sku)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_barcode(self, barcode: str) -> Optional[Product]:
        """Retrieve a product by its barcode."""
        stmt = select(Product).where(Product.barcode == barcode)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        query: Optional[str],
        filters: ProductFilters,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """Search products with partial name matching and exact SKU/barcode matching.

        Search logic:
        - Partial match (ilike) on product name
        - Exact match on SKU
        - Exact match on barcode
        Results are combined with OR logic for the search query.
        Only active products are returned by default.
        """
        stmt = select(Product)
        count_stmt = select(func.count()).select_from(Product)

        # Apply is_active filter (default to only active products)
        if filters.is_active is not None:
            stmt = stmt.where(Product.is_active == filters.is_active)
            count_stmt = count_stmt.where(Product.is_active == filters.is_active)
        else:
            # Default: only show active products
            stmt = stmt.where(Product.is_active.is_(True))
            count_stmt = count_stmt.where(Product.is_active.is_(True))

        # Apply category filter
        if filters.category_id is not None:
            stmt = stmt.where(Product.category_id == filters.category_id)
            count_stmt = count_stmt.where(Product.category_id == filters.category_id)

        # Apply search query (partial name match OR exact SKU/barcode match)
        if query:
            search_term = f"%{query}%"
            search_condition = or_(
                Product.name.ilike(search_term),
                Product.sku == query,
                Product.barcode == query,
            )
            stmt = stmt.where(search_condition)
            count_stmt = count_stmt.where(search_condition)

        # Get total count
        count_result = await self._session.execute(count_stmt)
        total_count = count_result.scalar_one()

        # Apply ordering and pagination
        stmt = stmt.order_by(Product.created_at.desc())
        stmt = stmt.offset(pagination.offset).limit(pagination.limit)

        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return PaginatedResult(items=items, total_count=total_count)

    async def update(
        self,
        product_id: uuid.UUID,
        **kwargs: object,
    ) -> Optional[Product]:
        """Update a product's fields by ID."""
        product = await self.get_by_id(product_id)
        if product is None:
            return None

        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)

        await self._session.flush()
        await self._session.refresh(product)
        return product

    async def update_stock(
        self,
        product_id: uuid.UUID,
        quantity_change: int,
    ) -> Optional[Product]:
        """Update a product's stock by a relative quantity change.

        Adds the quantity_change to the current stock. Use negative values
        to decrement stock.
        """
        product = await self.get_by_id(product_id)
        if product is None:
            return None

        product.stock = product.stock + quantity_change

        await self._session.flush()
        await self._session.refresh(product)
        return product

    async def get_low_stock(
        self,
        threshold: int,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """Retrieve active products with stock at or below the given threshold."""
        # Count total matching records
        count_stmt = (
            select(func.count())
            .select_from(Product)
            .where(Product.is_active.is_(True))
            .where(Product.stock <= threshold)
        )
        count_result = await self._session.execute(count_stmt)
        total_count = count_result.scalar_one()

        # Fetch paginated results sorted by stock ascending (lowest first)
        stmt = (
            select(Product)
            .where(Product.is_active.is_(True))
            .where(Product.stock <= threshold)
            .order_by(Product.stock.asc(), Product.name.asc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())

        return PaginatedResult(items=items, total_count=total_count)

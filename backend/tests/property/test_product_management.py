"""Property-based tests for product management.

Feature: vendora-pos-foundation
Property 16: Product SKU and barcode uniqueness
Property 17: Product partial update correctness
Property 18: Soft delete preserves product record
Property 19: Product search returns only active products with correct matching

Validates: Requirements 6.2, 6.3, 6.4, 6.5, 6.7, 7.1

These tests verify ProductService behavior using property-based testing
with Hypothesis strategies and AsyncMock for repositories.
"""

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

# Set environment variables before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-property-tests-minimum-length")

from app.core.dependencies import PaginationParams
from app.core.exceptions import ConflictException
from app.domain.interfaces import PaginatedResult, ProductFilters
from app.models.product import Product
from app.services.product_service import ProductService


# --- Strategies ---

product_name_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "Zs"),
        blacklist_characters="\x00\n\r\t",
    ),
    min_size=1,
    max_size=255,
).filter(lambda s: len(s.strip()) > 0)

sku_strategy = st.from_regex(r"[A-Z]{2,5}-[0-9]{3,8}", fullmatch=True)

barcode_strategy = st.one_of(
    st.none(),
    st.from_regex(r"[0-9]{8,13}", fullmatch=True),
)

non_null_barcode_strategy = st.from_regex(r"[0-9]{8,13}", fullmatch=True)

price_strategy = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

stock_strategy = st.integers(min_value=0, max_value=999999)

category_id_strategy = st.one_of(st.none(), st.uuids())

product_id_strategy = st.uuids()

page_strategy = st.integers(min_value=1, max_value=100)
page_size_strategy = st.integers(min_value=1, max_value=100)

search_query_strategy = st.one_of(
    st.none(),
    st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N", "Zs"),
            blacklist_characters="\x00\n\r\t",
        ),
        min_size=1,
        max_size=50,
    ),
)


# --- Helpers ---


def _make_mock_product(
    product_id: Optional[uuid.UUID] = None,
    name: str = "Test Product",
    sku: str = "TST-001",
    barcode: Optional[str] = None,
    price: Decimal = Decimal("9.99"),
    stock: int = 100,
    category_id: Optional[uuid.UUID] = None,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock Product object with all required attributes."""
    product = MagicMock(spec=Product)
    product.id = product_id or uuid.uuid4()
    product.name = name
    product.sku = sku
    product.barcode = barcode
    product.price = price
    product.stock = stock
    product.category_id = category_id
    product.is_active = is_active
    product.created_at = datetime.now(timezone.utc)
    product.updated_at = datetime.now(timezone.utc)
    return product


# --- Property 16: Product SKU and barcode uniqueness ---


class TestProductSkuAndBarcodeUniqueness:
    """**Validates: Requirements 6.2, 6.3, 6.4**

    Property 16: Product SKU and barcode uniqueness.
    For any SKU/barcode that already exists, create_product raises ConflictException.
    """

    @given(
        name=product_name_strategy,
        sku=sku_strategy,
        price=price_strategy,
        stock=stock_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_duplicate_sku_raises_conflict(
        self, name: str, sku: str, price: Decimal, stock: int
    ):
        """For any SKU that already exists, create_product raises ConflictException."""
        product_repo = AsyncMock()
        category_repo = AsyncMock()

        # Simulate existing product with same SKU
        existing_product = _make_mock_product(sku=sku)
        product_repo.get_by_sku.return_value = existing_product
        product_repo.get_by_barcode.return_value = None

        service = ProductService(
            product_repo=product_repo, category_repo=category_repo
        )

        with pytest.raises(ConflictException) as exc_info:
            await service.create_product(
                name=name,
                sku=sku,
                price=price,
                stock=stock,
                barcode=None,
                category_id=None,
            )

        assert "sku" in exc_info.value.message.lower()

    @given(
        name=product_name_strategy,
        sku=sku_strategy,
        barcode=non_null_barcode_strategy,
        price=price_strategy,
        stock=stock_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_duplicate_barcode_raises_conflict(
        self, name: str, sku: str, barcode: str, price: Decimal, stock: int
    ):
        """For any barcode that already exists, create_product raises ConflictException."""
        product_repo = AsyncMock()
        category_repo = AsyncMock()

        # SKU is unique (no conflict)
        product_repo.get_by_sku.return_value = None
        # Simulate existing product with same barcode
        existing_product = _make_mock_product(barcode=barcode)
        product_repo.get_by_barcode.return_value = existing_product

        service = ProductService(
            product_repo=product_repo, category_repo=category_repo
        )

        with pytest.raises(ConflictException) as exc_info:
            await service.create_product(
                name=name,
                sku=sku,
                price=price,
                stock=stock,
                barcode=barcode,
                category_id=None,
            )

        assert "barcode" in exc_info.value.message.lower()

    @given(
        product_id=product_id_strategy,
        existing_sku=sku_strategy,
        new_sku=sku_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_update_to_existing_sku_raises_conflict(
        self, product_id: uuid.UUID, existing_sku: str, new_sku: str
    ):
        """For any update changing SKU to one that exists, raises ConflictException."""
        assume(existing_sku != new_sku)

        product_repo = AsyncMock()
        category_repo = AsyncMock()

        # Current product has existing_sku
        current_product = _make_mock_product(product_id=product_id, sku=existing_sku)
        product_repo.get_by_id.return_value = current_product
        # Another product already has new_sku
        other_product = _make_mock_product(sku=new_sku)
        product_repo.get_by_sku.return_value = other_product

        service = ProductService(
            product_repo=product_repo, category_repo=category_repo
        )

        with pytest.raises(ConflictException) as exc_info:
            await service.update_product(product_id, sku=new_sku)

        assert "sku" in exc_info.value.message.lower()


# --- Property 17: Product partial update correctness ---


class TestProductPartialUpdateCorrectness:
    """**Validates: Requirements 6.5**

    Property 17: Product partial update correctness.
    For any partial update, only the provided fields are passed to the repository.
    """

    @given(
        product_id=product_id_strategy,
        new_name=st.one_of(st.none(), product_name_strategy),
        new_sku=st.one_of(st.none(), sku_strategy),
        new_barcode=st.one_of(st.none(), non_null_barcode_strategy),
        new_price=st.one_of(st.none(), price_strategy),
        new_stock=st.one_of(st.none(), stock_strategy),
        new_is_active=st.one_of(st.none(), st.booleans()),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_update_only_passes_provided_fields_to_repo(
        self,
        product_id: uuid.UUID,
        new_name: Optional[str],
        new_sku: Optional[str],
        new_barcode: Optional[str],
        new_price: Optional[Decimal],
        new_stock: Optional[int],
        new_is_active: Optional[bool],
    ):
        """For any combination of update fields, only provided (non-None) fields
        are passed to the repository update method."""
        # Skip if all fields are None (nothing to update)
        assume(
            new_name is not None
            or new_sku is not None
            or new_barcode is not None
            or new_price is not None
            or new_stock is not None
            or new_is_active is not None
        )

        product_repo = AsyncMock()
        category_repo = AsyncMock()

        existing_product = _make_mock_product(
            product_id=product_id,
            sku="ORIG-001",
            barcode="1234567890",
        )
        product_repo.get_by_id.return_value = existing_product
        # No uniqueness conflicts
        product_repo.get_by_sku.return_value = None
        product_repo.get_by_barcode.return_value = None

        updated_product = _make_mock_product(product_id=product_id)
        product_repo.update.return_value = updated_product

        service = ProductService(
            product_repo=product_repo, category_repo=category_repo
        )

        await service.update_product(
            product_id,
            name=new_name,
            sku=new_sku,
            barcode=new_barcode,
            price=new_price,
            stock=new_stock,
            is_active=new_is_active,
        )

        # Verify repo.update was called
        product_repo.update.assert_called_once()
        call_args = product_repo.update.call_args

        # First positional arg is product_id
        passed_product_id = call_args[0][0] if call_args[0] else None
        assert passed_product_id == product_id

        # Get the kwargs passed to repo.update
        update_kwargs = call_args[1] if call_args[1] else {}

        # Allowed updatable fields
        allowed_fields = {"name", "sku", "barcode", "price", "stock", "category_id", "is_active"}

        # All keys in update_kwargs must be in allowed_fields
        for key in update_kwargs:
            assert key in allowed_fields, (
                f"Disallowed field '{key}' was passed to repository update"
            )

        # Verify each provided field is present in kwargs
        if new_name is not None:
            assert "name" in update_kwargs
            assert update_kwargs["name"] == new_name.strip()
        else:
            assert "name" not in update_kwargs

        if new_sku is not None:
            assert "sku" in update_kwargs
            assert update_kwargs["sku"] == new_sku.strip()
        else:
            assert "sku" not in update_kwargs

        if new_barcode is not None:
            assert "barcode" in update_kwargs
        else:
            assert "barcode" not in update_kwargs

        if new_price is not None:
            assert "price" in update_kwargs
            assert update_kwargs["price"] == new_price
        else:
            assert "price" not in update_kwargs

        if new_stock is not None:
            assert "stock" in update_kwargs
            assert update_kwargs["stock"] == new_stock
        else:
            assert "stock" not in update_kwargs

        if new_is_active is not None:
            assert "is_active" in update_kwargs
            assert update_kwargs["is_active"] == new_is_active
        else:
            assert "is_active" not in update_kwargs


# --- Property 18: Soft delete preserves product record ---


class TestSoftDeletePreservesProductRecord:
    """**Validates: Requirements 6.7**

    Property 18: Soft delete preserves product record.
    For any soft delete, the product's is_active is set to false (not physically deleted).
    The record still exists in the database.
    """

    @given(
        product_id=product_id_strategy,
        name=product_name_strategy,
        sku=sku_strategy,
        price=price_strategy,
        stock=stock_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_soft_delete_sets_is_active_false(
        self,
        product_id: uuid.UUID,
        name: str,
        sku: str,
        price: Decimal,
        stock: int,
    ):
        """For any product soft delete, the service calls repo.update with
        is_active=False, preserving the record (not physically deleting it)."""
        product_repo = AsyncMock()
        category_repo = AsyncMock()

        existing_product = _make_mock_product(
            product_id=product_id,
            name=name,
            sku=sku,
            price=price,
            stock=stock,
            is_active=True,
        )
        product_repo.get_by_id.return_value = existing_product

        # The updated product returned after soft delete
        soft_deleted_product = _make_mock_product(
            product_id=product_id,
            name=name,
            sku=sku,
            price=price,
            stock=stock,
            is_active=False,
        )
        product_repo.update.return_value = soft_deleted_product

        service = ProductService(
            product_repo=product_repo, category_repo=category_repo
        )

        result = await service.soft_delete_product(product_id)

        # Verify repo.update was called with is_active=False
        product_repo.update.assert_called_once()
        call_args = product_repo.update.call_args
        passed_product_id = call_args[0][0] if call_args[0] else None
        update_kwargs = call_args[1] if call_args[1] else {}

        assert passed_product_id == product_id
        assert "is_active" in update_kwargs
        assert update_kwargs["is_active"] is False

        # Verify no physical delete method was called
        assert not hasattr(product_repo, "delete") or not product_repo.delete.called

        # The returned product has is_active=False
        assert result.is_active is False


# --- Property 19: Product search returns only active products with correct matching ---


class TestProductSearchReturnsOnlyActiveProducts:
    """**Validates: Requirements 7.1**

    Property 19: Product search returns only active products with correct matching.
    For any search, the is_active filter defaults to True so only active products
    are returned.
    """

    @given(
        query=search_query_strategy,
        page=page_strategy,
        page_size=page_size_strategy,
        category_id=st.one_of(st.none(), st.uuids()),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_search_passes_is_active_true_filter(
        self,
        query: Optional[str],
        page: int,
        page_size: int,
        category_id: Optional[uuid.UUID],
    ):
        """For any search query, the service passes is_active filter to the
        repository, ensuring only active products are returned by default."""
        product_repo = AsyncMock()
        category_repo = AsyncMock()

        # Return some mock active products
        mock_products = [
            _make_mock_product(is_active=True) for _ in range(min(3, page_size))
        ]
        product_repo.search.return_value = PaginatedResult(
            items=mock_products, total_count=len(mock_products)
        )

        service = ProductService(
            product_repo=product_repo, category_repo=category_repo
        )

        filters = ProductFilters(category_id=category_id, is_active=True)
        pagination = PaginationParams(page=page, page_size=page_size)

        result = await service.search_products(
            query=query, filters=filters, pagination=pagination
        )

        # Verify search was called with the correct filters
        product_repo.search.assert_called_once()
        call_kwargs = product_repo.search.call_args[1]

        # The filters passed to repo should have is_active=True
        assert call_kwargs["filters"].is_active is True

        # All returned items should be active
        for item in result.items:
            assert item.is_active is True

    @given(
        query=search_query_strategy,
        page=page_strategy,
        page_size=page_size_strategy,
        total_count=st.integers(min_value=0, max_value=200),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_search_results_count_does_not_exceed_page_size(
        self,
        query: Optional[str],
        page: int,
        page_size: int,
        total_count: int,
    ):
        """For any search, the returned items count does not exceed page_size."""
        product_repo = AsyncMock()
        category_repo = AsyncMock()

        # Calculate expected items on this page
        items_on_page = min(page_size, max(0, total_count - (page - 1) * page_size))
        items_on_page = max(0, items_on_page)

        mock_products = [
            _make_mock_product(is_active=True) for _ in range(items_on_page)
        ]
        product_repo.search.return_value = PaginatedResult(
            items=mock_products, total_count=total_count
        )

        service = ProductService(
            product_repo=product_repo, category_repo=category_repo
        )

        filters = ProductFilters(is_active=True)
        pagination = PaginationParams(page=page, page_size=page_size)

        result = await service.search_products(
            query=query, filters=filters, pagination=pagination
        )

        # Result count must not exceed page_size
        assert len(result.items) <= page_size, (
            f"Returned {len(result.items)} items but page_size is {page_size}"
        )

        # Total count must be non-negative
        assert result.total_count >= 0

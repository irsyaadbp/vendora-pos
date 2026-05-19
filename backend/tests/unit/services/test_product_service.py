"""Unit tests for ProductService."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

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
from app.services.product_service import ProductService


# --- Helpers ---


def _make_product(
    product_id: Optional[uuid.UUID] = None,
    name: str = "Test Product",
    sku: str = "SKU-001",
    barcode: Optional[str] = "1234567890",
    price: Decimal = Decimal("19.99"),
    stock: int = 100,
    category_id: Optional[uuid.UUID] = None,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock Product object."""
    product = MagicMock()
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


def _make_category(
    category_id: Optional[uuid.UUID] = None,
    name: str = "Test Category",
    description: Optional[str] = None,
) -> MagicMock:
    """Create a mock Category object."""
    category = MagicMock()
    category.id = category_id or uuid.uuid4()
    category.name = name
    category.description = description
    category.created_at = datetime.now(timezone.utc)
    return category


def _create_service(
    product_repo: Optional[AsyncMock] = None,
    category_repo: Optional[AsyncMock] = None,
) -> ProductService:
    """Create a ProductService with mock repositories."""
    return ProductService(
        product_repo=product_repo or AsyncMock(spec=ProductRepositoryInterface),
        category_repo=category_repo or AsyncMock(spec=CategoryRepositoryInterface),
    )



# --- Create Product Tests ---


class TestProductServiceCreateProduct:
    """Tests for ProductService.create_product()."""

    @pytest.mark.asyncio
    async def test_create_product_success(self) -> None:
        """Successful product creation returns the created product."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_sku.return_value = None
        product_repo.get_by_barcode.return_value = None
        created_product = _make_product()
        product_repo.create.return_value = created_product

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        result = await service.create_product(
            name="Test Product",
            sku="SKU-001",
            price=Decimal("19.99"),
            stock=100,
            barcode="1234567890",
        )

        assert result == created_product
        product_repo.get_by_sku.assert_called_once_with("SKU-001")
        product_repo.get_by_barcode.assert_called_once_with("1234567890")
        product_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_product_with_category(self) -> None:
        """Product creation with valid category_id succeeds."""
        cat_id = uuid.uuid4()
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_sku.return_value = None
        product_repo.get_by_barcode.return_value = None
        category_repo.get_by_id.return_value = _make_category(category_id=cat_id)
        product_repo.create.return_value = _make_product(category_id=cat_id)

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        result = await service.create_product(
            name="Test Product",
            sku="SKU-001",
            price=Decimal("19.99"),
            stock=100,
            category_id=cat_id,
        )

        assert result.category_id == cat_id
        category_repo.get_by_id.assert_called_once_with(cat_id)

    @pytest.mark.asyncio
    async def test_create_product_invalid_category_raises_not_found(self) -> None:
        """Product creation with non-existent category raises NotFoundException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_sku.return_value = None
        category_repo.get_by_id.return_value = None

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        with pytest.raises(NotFoundException) as exc_info:
            await service.create_product(
                name="Test Product",
                sku="SKU-001",
                price=Decimal("19.99"),
                stock=100,
                category_id=uuid.uuid4(),
            )

        assert "Category not found" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_create_product_duplicate_sku_raises_conflict(self) -> None:
        """Creating a product with existing SKU raises ConflictException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_sku.return_value = _make_product(sku="EXISTING-SKU")

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        with pytest.raises(ConflictException) as exc_info:
            await service.create_product(
                name="Test Product",
                sku="EXISTING-SKU",
                price=Decimal("19.99"),
                stock=100,
            )

        assert "SKU already exists" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_create_product_duplicate_barcode_raises_conflict(self) -> None:
        """Creating a product with existing barcode raises ConflictException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_sku.return_value = None
        product_repo.get_by_barcode.return_value = _make_product(barcode="DUPE-BARCODE")

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        with pytest.raises(ConflictException) as exc_info:
            await service.create_product(
                name="Test Product",
                sku="SKU-001",
                price=Decimal("19.99"),
                stock=100,
                barcode="DUPE-BARCODE",
            )

        assert "barcode already exists" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_create_product_empty_name_raises_validation(self) -> None:
        """Creating a product with empty name raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.create_product(
                name="",
                sku="SKU-001",
                price=Decimal("19.99"),
                stock=100,
            )

        assert any(e.field == "name" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_create_product_name_too_long_raises_validation(self) -> None:
        """Creating a product with name > 255 chars raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.create_product(
                name="A" * 256,
                sku="SKU-001",
                price=Decimal("19.99"),
                stock=100,
            )

        assert any(e.field == "name" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_create_product_empty_sku_raises_validation(self) -> None:
        """Creating a product with empty SKU raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.create_product(
                name="Test Product",
                sku="",
                price=Decimal("19.99"),
                stock=100,
            )

        assert any(e.field == "sku" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_create_product_sku_too_long_raises_validation(self) -> None:
        """Creating a product with SKU > 100 chars raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.create_product(
                name="Test Product",
                sku="S" * 101,
                price=Decimal("19.99"),
                stock=100,
            )

        assert any(e.field == "sku" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_create_product_price_too_low_raises_validation(self) -> None:
        """Creating a product with price < 0.01 raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.create_product(
                name="Test Product",
                sku="SKU-001",
                price=Decimal("0.00"),
                stock=100,
            )

        assert any(e.field == "price" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_create_product_price_too_high_raises_validation(self) -> None:
        """Creating a product with price > 999999999.99 raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.create_product(
                name="Test Product",
                sku="SKU-001",
                price=Decimal("1000000000.00"),
                stock=100,
            )

        assert any(e.field == "price" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_create_product_negative_stock_raises_validation(self) -> None:
        """Creating a product with negative stock raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.create_product(
                name="Test Product",
                sku="SKU-001",
                price=Decimal("19.99"),
                stock=-1,
            )

        assert any(e.field == "stock" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_create_product_strips_name_and_sku(self) -> None:
        """Product creation strips whitespace from name and SKU."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_sku.return_value = None
        product_repo.create.return_value = _make_product()

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        await service.create_product(
            name="  Test Product  ",
            sku="  SKU-001  ",
            price=Decimal("19.99"),
            stock=100,
        )

        call_kwargs = product_repo.create.call_args[1]
        assert call_kwargs["name"] == "Test Product"
        assert call_kwargs["sku"] == "SKU-001"



# --- Update Product Tests ---


class TestProductServiceUpdateProduct:
    """Tests for ProductService.update_product()."""

    @pytest.mark.asyncio
    async def test_update_product_success(self) -> None:
        """Successful product update returns the updated product."""
        product_id = uuid.uuid4()
        existing = _make_product(product_id=product_id, name="Old Name")
        updated = _make_product(product_id=product_id, name="New Name")

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_id.return_value = existing
        product_repo.update.return_value = updated

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        result = await service.update_product(product_id, name="New Name")

        assert result == updated
        product_repo.update.assert_called_once_with(product_id, name="New Name")

    @pytest.mark.asyncio
    async def test_update_product_not_found_raises_not_found(self) -> None:
        """Updating a non-existent product raises NotFoundException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_id.return_value = None

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        with pytest.raises(NotFoundException):
            await service.update_product(uuid.uuid4(), name="New Name")

    @pytest.mark.asyncio
    async def test_update_product_sku_uniqueness_check(self) -> None:
        """Updating SKU to an existing SKU raises ConflictException."""
        product_id = uuid.uuid4()
        existing = _make_product(product_id=product_id, sku="OLD-SKU")
        other_product = _make_product(sku="TAKEN-SKU")

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_id.return_value = existing
        product_repo.get_by_sku.return_value = other_product

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        with pytest.raises(ConflictException) as exc_info:
            await service.update_product(product_id, sku="TAKEN-SKU")

        assert "SKU already exists" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_update_product_same_sku_no_conflict(self) -> None:
        """Updating with the same SKU does not trigger conflict."""
        product_id = uuid.uuid4()
        existing = _make_product(product_id=product_id, sku="SAME-SKU")
        updated = _make_product(product_id=product_id, sku="SAME-SKU")

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_id.return_value = existing
        product_repo.update.return_value = updated

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        result = await service.update_product(product_id, sku="SAME-SKU")

        assert result == updated
        product_repo.get_by_sku.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_product_barcode_uniqueness_check(self) -> None:
        """Updating barcode to an existing barcode raises ConflictException."""
        product_id = uuid.uuid4()
        existing = _make_product(product_id=product_id, barcode="OLD-BARCODE")
        other_product = _make_product(barcode="TAKEN-BARCODE")

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_id.return_value = existing
        product_repo.get_by_barcode.return_value = other_product

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        with pytest.raises(ConflictException) as exc_info:
            await service.update_product(product_id, barcode="TAKEN-BARCODE")

        assert "barcode already exists" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_update_product_same_barcode_no_conflict(self) -> None:
        """Updating with the same barcode does not trigger conflict."""
        product_id = uuid.uuid4()
        existing = _make_product(product_id=product_id, barcode="SAME-BARCODE")
        updated = _make_product(product_id=product_id, barcode="SAME-BARCODE")

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_id.return_value = existing
        product_repo.update.return_value = updated

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        result = await service.update_product(product_id, barcode="SAME-BARCODE")

        assert result == updated
        product_repo.get_by_barcode.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_product_validation_errors(self) -> None:
        """Updating with invalid fields raises ValidationException."""
        product_id = uuid.uuid4()
        existing = _make_product(product_id=product_id)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_id.return_value = existing

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.update_product(
                product_id,
                name="",
                price=Decimal("0.00"),
                stock=-5,
            )

        fields = [e.field for e in exc_info.value.errors]
        assert "name" in fields
        assert "price" in fields
        assert "stock" in fields

    @pytest.mark.asyncio
    async def test_update_product_no_fields_returns_existing(self) -> None:
        """Updating with no fields returns the existing product unchanged."""
        product_id = uuid.uuid4()
        existing = _make_product(product_id=product_id)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_id.return_value = existing

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        result = await service.update_product(product_id)

        assert result == existing
        product_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_product_partial_update(self) -> None:
        """Updating only some fields passes only those to repository."""
        product_id = uuid.uuid4()
        existing = _make_product(product_id=product_id)
        updated = _make_product(product_id=product_id, price=Decimal("29.99"))

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_id.return_value = existing
        product_repo.update.return_value = updated

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        await service.update_product(product_id, price=Decimal("29.99"))

        product_repo.update.assert_called_once_with(product_id, price=Decimal("29.99"))



# --- Soft Delete Product Tests ---


class TestProductServiceSoftDeleteProduct:
    """Tests for ProductService.soft_delete_product()."""

    @pytest.mark.asyncio
    async def test_soft_delete_product_success(self) -> None:
        """Successful soft delete sets is_active to false."""
        product_id = uuid.uuid4()
        existing = _make_product(product_id=product_id, is_active=True)
        deleted = _make_product(product_id=product_id, is_active=False)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_id.return_value = existing
        product_repo.update.return_value = deleted

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        result = await service.soft_delete_product(product_id)

        assert result == deleted
        product_repo.update.assert_called_once_with(product_id, is_active=False)

    @pytest.mark.asyncio
    async def test_soft_delete_product_not_found_raises_not_found(self) -> None:
        """Soft deleting a non-existent product raises NotFoundException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.get_by_id.return_value = None

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        with pytest.raises(NotFoundException):
            await service.soft_delete_product(uuid.uuid4())


# --- Search Products Tests ---


class TestProductServiceSearchProducts:
    """Tests for ProductService.search_products()."""

    @pytest.mark.asyncio
    async def test_search_products_delegates_to_repository(self) -> None:
        """search_products passes query, filters, and pagination to repository."""
        products = [_make_product() for _ in range(3)]
        paginated_result = PaginatedResult(items=products, total_count=3)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.search.return_value = paginated_result

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        filters = ProductFilters(category_id=uuid.uuid4(), is_active=True)
        pagination = PaginationParams(page=1, page_size=20)

        result = await service.search_products(
            query="test", filters=filters, pagination=pagination
        )

        assert result == paginated_result
        product_repo.search.assert_called_once_with(
            query="test", filters=filters, pagination=pagination
        )

    @pytest.mark.asyncio
    async def test_search_products_empty_result(self) -> None:
        """search_products returns empty result when no products match."""
        paginated_result = PaginatedResult(items=[], total_count=0)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        product_repo.search.return_value = paginated_result

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        filters = ProductFilters()
        pagination = PaginationParams(page=1, page_size=20)

        result = await service.search_products(
            query=None, filters=filters, pagination=pagination
        )

        assert result.items == []
        assert result.total_count == 0



# --- Category CRUD Tests ---


class TestProductServiceCreateCategory:
    """Tests for ProductService.create_category()."""

    @pytest.mark.asyncio
    async def test_create_category_success(self) -> None:
        """Successful category creation returns the created category."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        category_repo.get_by_name.return_value = None
        created_category = _make_category(name="Electronics")
        category_repo.create.return_value = created_category

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        result = await service.create_category(name="Electronics", description="Electronic items")

        assert result == created_category
        category_repo.get_by_name.assert_called_once_with("Electronics")
        category_repo.create.assert_called_once_with(
            name="Electronics", description="Electronic items"
        )

    @pytest.mark.asyncio
    async def test_create_category_duplicate_name_raises_conflict(self) -> None:
        """Creating a category with existing name raises ConflictException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        category_repo.get_by_name.return_value = _make_category(name="Existing")

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        with pytest.raises(ConflictException) as exc_info:
            await service.create_category(name="Existing")

        assert "category with this name already exists" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_create_category_empty_name_raises_validation(self) -> None:
        """Creating a category with empty name raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.create_category(name="")

        assert any(e.field == "name" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_create_category_name_too_long_raises_validation(self) -> None:
        """Creating a category with name > 100 chars raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.create_category(name="A" * 101)

        assert any(e.field == "name" for e in exc_info.value.errors)

    @pytest.mark.asyncio
    async def test_create_category_strips_name(self) -> None:
        """Category creation strips whitespace from name."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        category_repo.get_by_name.return_value = None
        category_repo.create.return_value = _make_category()

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        await service.create_category(name="  Electronics  ")

        category_repo.get_by_name.assert_called_once_with("Electronics")
        call_kwargs = category_repo.create.call_args[1]
        assert call_kwargs["name"] == "Electronics"


class TestProductServiceListCategories:
    """Tests for ProductService.list_categories()."""

    @pytest.mark.asyncio
    async def test_list_categories_delegates_to_repository(self) -> None:
        """list_categories passes pagination to the repository."""
        categories = [_make_category() for _ in range(3)]
        paginated_result = PaginatedResult(items=categories, total_count=3)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        category_repo.list.return_value = paginated_result

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        pagination = PaginationParams(page=1, page_size=20)
        result = await service.list_categories(pagination=pagination)

        assert result == paginated_result
        category_repo.list.assert_called_once_with(pagination=pagination)


class TestProductServiceUpdateCategory:
    """Tests for ProductService.update_category()."""

    @pytest.mark.asyncio
    async def test_update_category_success(self) -> None:
        """Successful category update returns the updated category."""
        cat_id = uuid.uuid4()
        existing = _make_category(category_id=cat_id, name="Old Name")
        updated = _make_category(category_id=cat_id, name="New Name")

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        category_repo.get_by_id.return_value = existing
        category_repo.get_by_name.return_value = None
        category_repo.update.return_value = updated

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        result = await service.update_category(cat_id, name="New Name")

        assert result == updated

    @pytest.mark.asyncio
    async def test_update_category_not_found_raises_not_found(self) -> None:
        """Updating a non-existent category raises NotFoundException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        category_repo.get_by_id.return_value = None

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        with pytest.raises(NotFoundException):
            await service.update_category(uuid.uuid4(), name="New Name")

    @pytest.mark.asyncio
    async def test_update_category_duplicate_name_raises_conflict(self) -> None:
        """Updating category name to existing name raises ConflictException."""
        cat_id = uuid.uuid4()
        existing = _make_category(category_id=cat_id, name="Old Name")
        other = _make_category(name="Taken Name")

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        category_repo.get_by_id.return_value = existing
        category_repo.get_by_name.return_value = other

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        with pytest.raises(ConflictException) as exc_info:
            await service.update_category(cat_id, name="Taken Name")

        assert "category with this name already exists" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_update_category_same_name_no_conflict(self) -> None:
        """Updating with the same name does not trigger conflict."""
        cat_id = uuid.uuid4()
        existing = _make_category(category_id=cat_id, name="Same Name")
        updated = _make_category(category_id=cat_id, name="Same Name")

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        category_repo.get_by_id.return_value = existing
        category_repo.update.return_value = updated

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        result = await service.update_category(cat_id, name="Same Name")

        assert result == updated
        category_repo.get_by_name.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_category_empty_name_raises_validation(self) -> None:
        """Updating category with empty name raises ValidationException."""
        cat_id = uuid.uuid4()
        existing = _make_category(category_id=cat_id)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        category_repo.get_by_id.return_value = existing

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.update_category(cat_id, name="   ")

        assert any(e.field == "name" for e in exc_info.value.errors)


class TestProductServiceDeleteCategory:
    """Tests for ProductService.delete_category()."""

    @pytest.mark.asyncio
    async def test_delete_category_success(self) -> None:
        """Successful category deletion calls repository delete."""
        cat_id = uuid.uuid4()
        existing = _make_category(category_id=cat_id)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        category_repo.get_by_id.return_value = existing

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        await service.delete_category(cat_id)

        category_repo.delete.assert_called_once_with(cat_id)

    @pytest.mark.asyncio
    async def test_delete_category_not_found_raises_not_found(self) -> None:
        """Deleting a non-existent category raises NotFoundException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        category_repo = AsyncMock(spec=CategoryRepositoryInterface)
        category_repo.get_by_id.return_value = None

        service = _create_service(product_repo=product_repo, category_repo=category_repo)

        with pytest.raises(NotFoundException):
            await service.delete_category(uuid.uuid4())

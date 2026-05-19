"""Property-based tests for transaction processing.

Feature: vendora-pos-foundation
Property 22: Transaction stock validation
Property 23: Transaction atomicity and stock decrement
Property 24: Transaction receipt completeness
Property 25: Staff transaction isolation

Validates: Requirements 7.6, 7.7, 7.8, 7.9, 7.11, 7.13

These tests verify TransactionService behavior using property-based testing
with Hypothesis strategies and AsyncMock for repositories.
"""

import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

# Set environment variables before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-property-tests-minimum-length")

from app.core.dependencies import PaginationParams
from app.core.exceptions import ValidationException, NotFoundException
from app.domain.interfaces import PaginatedResult, TransactionFilters
from app.models.product import Product
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.enums import DiscountType, PaymentMethod, UserRole
from app.services.transaction_service import (
    TransactionService,
    TransactionItemInput,
    TransactionReceipt,
)


# --- Strategies ---

payment_method_strategy = st.sampled_from(list(PaymentMethod))

discount_type_strategy = st.sampled_from(list(DiscountType))

quantity_strategy = st.integers(min_value=1, max_value=50)

stock_strategy = st.integers(min_value=0, max_value=200)

price_strategy = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("9999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

percentage_discount_strategy = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("100"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

fixed_discount_strategy = st.decimals(
    min_value=Decimal("0"),
    max_value=Decimal("99999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

# Strategy for generating a list of transaction items (1-5 items)
item_count_strategy = st.integers(min_value=1, max_value=5)


# --- Helpers ---


def _make_mock_product(
    product_id: Optional[uuid.UUID] = None,
    name: str = "Test Product",
    sku: str = "TST-001",
    price: Decimal = Decimal("9.99"),
    stock: int = 100,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock Product object with all required attributes."""
    product = MagicMock(spec=Product)
    product.id = product_id or uuid.uuid4()
    product.name = name
    product.sku = sku
    product.barcode = None
    product.price = price
    product.stock = stock
    product.category_id = None
    product.is_active = is_active
    product.created_at = datetime.now(timezone.utc)
    product.updated_at = datetime.now(timezone.utc)
    return product


def _make_mock_user(
    user_id: Optional[uuid.UUID] = None,
    role: UserRole = UserRole.staff,
    full_name: str = "Test User",
) -> MagicMock:
    """Create a mock User object."""
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.full_name = full_name
    user.email = "test@example.com"
    user.role = role
    user.is_active = True
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


def _make_mock_transaction(
    transaction_id: Optional[uuid.UUID] = None,
    cashier_id: Optional[uuid.UUID] = None,
    total_amount: Decimal = Decimal("100.00"),
    discount_amount: Decimal = Decimal("0.00"),
    payment_method: PaymentMethod = PaymentMethod.cash,
    cashier_name: str = "Test Cashier",
) -> MagicMock:
    """Create a mock Transaction object."""
    txn = MagicMock(spec=Transaction)
    txn.id = transaction_id or uuid.uuid4()
    txn.cashier_id = cashier_id or uuid.uuid4()
    txn.total_amount = total_amount
    txn.discount_amount = discount_amount
    txn.payment_method = payment_method
    txn.status = "completed"
    txn.created_at = datetime.now(timezone.utc)
    # Mock cashier relationship
    cashier_mock = MagicMock()
    cashier_mock.full_name = cashier_name
    txn.cashier = cashier_mock
    return txn


# --- Property 22: Transaction stock validation ---


class TestTransactionStockValidation:
    """**Validates: Requirements 7.6, 7.7, 7.8**

    Property 22: Transaction stock validation.
    For any transaction submission, the system SHALL accept the transaction if and
    only if every item's requested quantity is less than or equal to the product's
    current stock AND the discount amount does not exceed the transaction subtotal.
    """

    @given(
        num_items=st.integers(min_value=1, max_value=5),
        payment_method=payment_method_strategy,
        data=st.data(),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_accepts_transaction_when_all_items_have_sufficient_stock(
        self, num_items: int, payment_method: PaymentMethod, data: st.DataObject
    ):
        """For any transaction where all items have quantity <= stock,
        the transaction is accepted (no ValidationException raised)."""
        txn_repo = AsyncMock()
        product_repo = AsyncMock()

        items = []
        products = {}
        cashier_id = uuid.uuid4()

        for i in range(num_items):
            product_id = uuid.uuid4()
            stock = data.draw(st.integers(min_value=1, max_value=200))
            quantity = data.draw(st.integers(min_value=1, max_value=stock))
            price = data.draw(price_strategy)

            product = _make_mock_product(
                product_id=product_id,
                name=f"Product {i}",
                sku=f"SKU-{i:03d}",
                price=price,
                stock=stock,
            )
            products[product_id] = product
            items.append(TransactionItemInput(product_id=product_id, quantity=quantity))

        # Configure product_repo.get_by_id to return the correct product
        async def get_by_id_side_effect(pid):
            return products.get(pid)

        product_repo.get_by_id.side_effect = get_by_id_side_effect

        # Configure txn_repo.create to return a mock transaction
        mock_txn = _make_mock_transaction(cashier_id=cashier_id)
        txn_repo.create.return_value = mock_txn

        service = TransactionService(txn_repo=txn_repo, product_repo=product_repo)

        # Should not raise
        result = await service.create_transaction(
            cashier_id=cashier_id,
            items=items,
            payment_method=payment_method,
        )

        assert result is not None
        assert isinstance(result, TransactionReceipt)

    @given(
        num_items=st.integers(min_value=1, max_value=5),
        payment_method=payment_method_strategy,
        data=st.data(),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_rejects_transaction_when_any_item_has_insufficient_stock(
        self, num_items: int, payment_method: PaymentMethod, data: st.DataObject
    ):
        """For any transaction where at least one item has quantity > stock,
        the transaction is rejected with a ValidationException."""
        txn_repo = AsyncMock()
        product_repo = AsyncMock()

        items = []
        products = {}
        cashier_id = uuid.uuid4()

        # Create items where at least one has insufficient stock
        insufficient_index = data.draw(st.integers(min_value=0, max_value=num_items - 1))

        for i in range(num_items):
            product_id = uuid.uuid4()
            price = data.draw(price_strategy)

            if i == insufficient_index:
                # This item has insufficient stock
                stock = data.draw(st.integers(min_value=0, max_value=10))
                quantity = data.draw(st.integers(min_value=stock + 1, max_value=stock + 50))
            else:
                # Sufficient stock
                stock = data.draw(st.integers(min_value=10, max_value=200))
                quantity = data.draw(st.integers(min_value=1, max_value=stock))

            product = _make_mock_product(
                product_id=product_id,
                name=f"Product {i}",
                sku=f"SKU-{i:03d}",
                price=price,
                stock=stock,
            )
            products[product_id] = product
            items.append(TransactionItemInput(product_id=product_id, quantity=quantity))

        async def get_by_id_side_effect(pid):
            return products.get(pid)

        product_repo.get_by_id.side_effect = get_by_id_side_effect

        service = TransactionService(txn_repo=txn_repo, product_repo=product_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_transaction(
                cashier_id=cashier_id,
                items=items,
                payment_method=payment_method,
            )

        assert "stock" in exc_info.value.message.lower()

    @given(
        price=price_strategy,
        quantity=st.integers(min_value=1, max_value=10),
        payment_method=payment_method_strategy,
        data=st.data(),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_rejects_transaction_when_discount_exceeds_subtotal(
        self, price: Decimal, quantity: int, payment_method: PaymentMethod, data: st.DataObject
    ):
        """For any transaction where the discount amount exceeds the subtotal,
        the transaction is rejected with a ValidationException."""
        txn_repo = AsyncMock()
        product_repo = AsyncMock()

        product_id = uuid.uuid4()
        cashier_id = uuid.uuid4()
        stock = quantity + 10  # Ensure sufficient stock

        product = _make_mock_product(
            product_id=product_id, price=price, stock=stock
        )

        product_repo.get_by_id.return_value = product

        items = [TransactionItemInput(product_id=product_id, quantity=quantity)]

        # Calculate subtotal and create a discount that exceeds it
        subtotal = price * Decimal(str(quantity))
        # Fixed discount greater than subtotal
        excess_discount = subtotal + data.draw(
            st.decimals(
                min_value=Decimal("0.01"),
                max_value=Decimal("1000.00"),
                places=2,
                allow_nan=False,
                allow_infinity=False,
            )
        )

        service = TransactionService(txn_repo=txn_repo, product_repo=product_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_transaction(
                cashier_id=cashier_id,
                items=items,
                payment_method=payment_method,
                discount_type=DiscountType.fixed,
                discount_value=excess_discount,
            )

        assert "discount" in exc_info.value.message.lower()


# --- Property 23: Transaction atomicity and stock decrement ---


class TestTransactionAtomicityAndStockDecrement:
    """**Validates: Requirements 7.9, 2.10**

    Property 23: Transaction atomicity and stock decrement.
    For any valid completed transaction, the stock of each purchased product SHALL
    decrease by exactly the purchased quantity, and if any step fails, no stock
    changes or records SHALL persist.
    """

    @given(
        num_items=st.integers(min_value=1, max_value=5),
        payment_method=payment_method_strategy,
        data=st.data(),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_transaction_calls_repo_create_with_correct_items(
        self, num_items: int, payment_method: PaymentMethod, data: st.DataObject
    ):
        """For any valid transaction, the repository create is called with
        item details that match the input quantities and prices, enabling
        atomic stock decrement."""
        txn_repo = AsyncMock()
        product_repo = AsyncMock()

        items = []
        products = {}
        cashier_id = uuid.uuid4()
        expected_items = []

        for i in range(num_items):
            product_id = uuid.uuid4()
            stock = data.draw(st.integers(min_value=10, max_value=200))
            quantity = data.draw(st.integers(min_value=1, max_value=stock))
            price = data.draw(price_strategy)

            product = _make_mock_product(
                product_id=product_id,
                name=f"Product {i}",
                sku=f"SKU-{i:03d}",
                price=price,
                stock=stock,
            )
            products[product_id] = product
            items.append(TransactionItemInput(product_id=product_id, quantity=quantity))
            expected_items.append({
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": price,
                "subtotal": Decimal(str(quantity)) * price,
            })

        async def get_by_id_side_effect(pid):
            return products.get(pid)

        product_repo.get_by_id.side_effect = get_by_id_side_effect

        mock_txn = _make_mock_transaction(cashier_id=cashier_id)
        txn_repo.create.return_value = mock_txn

        service = TransactionService(txn_repo=txn_repo, product_repo=product_repo)

        await service.create_transaction(
            cashier_id=cashier_id,
            items=items,
            payment_method=payment_method,
        )

        # Verify txn_repo.create was called exactly once (atomic operation)
        txn_repo.create.assert_called_once()
        call_kwargs = txn_repo.create.call_args[1]

        # Verify items passed to repo match expected quantities
        repo_items = call_kwargs["items"]
        assert len(repo_items) == num_items

        for i, repo_item in enumerate(repo_items):
            assert repo_item["product_id"] == expected_items[i]["product_id"]
            assert repo_item["quantity"] == expected_items[i]["quantity"]
            assert repo_item["unit_price"] == expected_items[i]["unit_price"]
            assert repo_item["subtotal"] == expected_items[i]["subtotal"]

    @given(
        payment_method=payment_method_strategy,
        data=st.data(),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_no_repo_create_called_on_validation_failure(
        self, payment_method: PaymentMethod, data: st.DataObject
    ):
        """For any transaction that fails validation (insufficient stock),
        the repository create method SHALL NOT be called, ensuring no
        partial records persist."""
        txn_repo = AsyncMock()
        product_repo = AsyncMock()

        product_id = uuid.uuid4()
        cashier_id = uuid.uuid4()
        stock = data.draw(st.integers(min_value=0, max_value=5))
        quantity = data.draw(st.integers(min_value=stock + 1, max_value=stock + 50))
        price = data.draw(price_strategy)

        product = _make_mock_product(
            product_id=product_id, price=price, stock=stock
        )
        product_repo.get_by_id.return_value = product

        items = [TransactionItemInput(product_id=product_id, quantity=quantity)]

        service = TransactionService(txn_repo=txn_repo, product_repo=product_repo)

        with pytest.raises(ValidationException):
            await service.create_transaction(
                cashier_id=cashier_id,
                items=items,
                payment_method=payment_method,
            )

        # Verify txn_repo.create was never called
        txn_repo.create.assert_not_called()

    @given(
        num_items=st.integers(min_value=1, max_value=5),
        payment_method=payment_method_strategy,
        data=st.data(),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_total_amount_equals_subtotal_minus_discount(
        self, num_items: int, payment_method: PaymentMethod, data: st.DataObject
    ):
        """For any valid transaction with a discount, the total_amount passed to
        the repository equals the subtotal minus the discount amount."""
        txn_repo = AsyncMock()
        product_repo = AsyncMock()

        items = []
        products = {}
        cashier_id = uuid.uuid4()
        subtotal = Decimal("0.00")

        for i in range(num_items):
            product_id = uuid.uuid4()
            stock = data.draw(st.integers(min_value=10, max_value=200))
            quantity = data.draw(st.integers(min_value=1, max_value=min(stock, 10)))
            price = data.draw(price_strategy)

            product = _make_mock_product(
                product_id=product_id,
                name=f"Product {i}",
                sku=f"SKU-{i:03d}",
                price=price,
                stock=stock,
            )
            products[product_id] = product
            items.append(TransactionItemInput(product_id=product_id, quantity=quantity))
            subtotal += Decimal(str(quantity)) * price

        # Apply a percentage discount that won't exceed subtotal
        discount_pct = data.draw(
            st.decimals(
                min_value=Decimal("0"),
                max_value=Decimal("50.00"),
                places=2,
                allow_nan=False,
                allow_infinity=False,
            )
        )
        expected_discount = (subtotal * discount_pct / Decimal("100")).quantize(Decimal("0.01"))
        expected_total = subtotal - expected_discount

        async def get_by_id_side_effect(pid):
            return products.get(pid)

        product_repo.get_by_id.side_effect = get_by_id_side_effect

        mock_txn = _make_mock_transaction(cashier_id=cashier_id)
        txn_repo.create.return_value = mock_txn

        service = TransactionService(txn_repo=txn_repo, product_repo=product_repo)

        await service.create_transaction(
            cashier_id=cashier_id,
            items=items,
            payment_method=payment_method,
            discount_type=DiscountType.percentage,
            discount_value=discount_pct,
        )

        # Verify the total_amount and discount_amount passed to repo
        call_kwargs = txn_repo.create.call_args[1]
        assert call_kwargs["total_amount"] == expected_total
        assert call_kwargs["discount_amount"] == expected_discount


# --- Property 24: Transaction receipt completeness ---


class TestTransactionReceiptCompleteness:
    """**Validates: Requirements 7.11**

    Property 24: Transaction receipt completeness.
    For any completed transaction, the returned receipt SHALL contain:
    transaction id, all items with quantities and unit prices, total amount,
    discount amount, payment method, cashier name, and timestamp.
    """

    @given(
        num_items=st.integers(min_value=1, max_value=5),
        payment_method=payment_method_strategy,
        data=st.data(),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_receipt_contains_all_required_fields(
        self, num_items: int, payment_method: PaymentMethod, data: st.DataObject
    ):
        """For any completed transaction, the receipt contains all required fields:
        id, items, total_amount, discount_amount, payment_method, cashier_name,
        and created_at."""
        txn_repo = AsyncMock()
        product_repo = AsyncMock()

        items = []
        products = {}
        cashier_id = uuid.uuid4()
        cashier_name = "Jane Doe"

        for i in range(num_items):
            product_id = uuid.uuid4()
            stock = data.draw(st.integers(min_value=10, max_value=200))
            quantity = data.draw(st.integers(min_value=1, max_value=stock))
            price = data.draw(price_strategy)

            product = _make_mock_product(
                product_id=product_id,
                name=f"Product {i}",
                sku=f"SKU-{i:03d}",
                price=price,
                stock=stock,
            )
            products[product_id] = product
            items.append(TransactionItemInput(product_id=product_id, quantity=quantity))

        async def get_by_id_side_effect(pid):
            return products.get(pid)

        product_repo.get_by_id.side_effect = get_by_id_side_effect

        txn_id = uuid.uuid4()
        created_at = datetime.now(timezone.utc)
        mock_txn = _make_mock_transaction(
            transaction_id=txn_id,
            cashier_id=cashier_id,
            cashier_name=cashier_name,
        )
        mock_txn.created_at = created_at
        txn_repo.create.return_value = mock_txn

        service = TransactionService(txn_repo=txn_repo, product_repo=product_repo)

        receipt = await service.create_transaction(
            cashier_id=cashier_id,
            items=items,
            payment_method=payment_method,
        )

        # Verify all required fields are present and non-None
        assert receipt.id is not None
        assert isinstance(receipt.id, uuid.UUID)
        assert receipt.items is not None
        assert len(receipt.items) == num_items
        assert receipt.total_amount is not None
        assert isinstance(receipt.total_amount, Decimal)
        assert receipt.discount_amount is not None
        assert isinstance(receipt.discount_amount, Decimal)
        assert receipt.payment_method is not None
        assert receipt.payment_method == payment_method
        assert receipt.cashier_name is not None
        assert len(receipt.cashier_name) > 0
        assert receipt.created_at is not None

    @given(
        num_items=st.integers(min_value=1, max_value=5),
        payment_method=payment_method_strategy,
        data=st.data(),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_receipt_items_match_input_quantities_and_prices(
        self, num_items: int, payment_method: PaymentMethod, data: st.DataObject
    ):
        """For any completed transaction, each receipt item contains the correct
        product_id, product_name, quantity, unit_price, and subtotal."""
        txn_repo = AsyncMock()
        product_repo = AsyncMock()

        items = []
        products = {}
        cashier_id = uuid.uuid4()
        expected_receipt_items = []

        for i in range(num_items):
            product_id = uuid.uuid4()
            stock = data.draw(st.integers(min_value=10, max_value=200))
            quantity = data.draw(st.integers(min_value=1, max_value=stock))
            price = data.draw(price_strategy)
            product_name = f"Product {i}"

            product = _make_mock_product(
                product_id=product_id,
                name=product_name,
                sku=f"SKU-{i:03d}",
                price=price,
                stock=stock,
            )
            products[product_id] = product
            items.append(TransactionItemInput(product_id=product_id, quantity=quantity))
            expected_receipt_items.append({
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "unit_price": price,
                "subtotal": Decimal(str(quantity)) * price,
            })

        async def get_by_id_side_effect(pid):
            return products.get(pid)

        product_repo.get_by_id.side_effect = get_by_id_side_effect

        mock_txn = _make_mock_transaction(cashier_id=cashier_id)
        txn_repo.create.return_value = mock_txn

        service = TransactionService(txn_repo=txn_repo, product_repo=product_repo)

        receipt = await service.create_transaction(
            cashier_id=cashier_id,
            items=items,
            payment_method=payment_method,
        )

        # Verify each receipt item matches expected values
        assert len(receipt.items) == num_items
        for i, receipt_item in enumerate(receipt.items):
            expected = expected_receipt_items[i]
            assert receipt_item.product_id == expected["product_id"]
            assert receipt_item.product_name == expected["product_name"]
            assert receipt_item.quantity == expected["quantity"]
            assert receipt_item.unit_price == expected["unit_price"]
            assert receipt_item.subtotal == expected["subtotal"]


# --- Property 25: Staff transaction isolation ---


class TestStaffTransactionIsolation:
    """**Validates: Requirements 7.13**

    Property 25: Staff transaction isolation.
    For any staff user requesting transaction history, the results SHALL contain
    only transactions where cashier_id equals that user's id.
    """

    @given(
        staff_id=st.uuids(),
        page=st.integers(min_value=1, max_value=10),
        page_size=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_staff_list_transactions_scopes_to_own_user(
        self, staff_id: uuid.UUID, page: int, page_size: int
    ):
        """For any staff user listing transactions, the service sets user_scope
        filter to the staff user's ID, ensuring only their transactions are returned."""
        txn_repo = AsyncMock()
        product_repo = AsyncMock()

        # Create a staff user
        staff_user = _make_mock_user(user_id=staff_id, role=UserRole.staff)

        # Mock repo to return empty results
        txn_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        service = TransactionService(txn_repo=txn_repo, product_repo=product_repo)

        filters = TransactionFilters()
        pagination = PaginationParams(page=page, page_size=page_size)

        await service.list_transactions(
            user=staff_user, filters=filters, pagination=pagination
        )

        # Verify the repo was called with user_scope set to staff user's ID
        txn_repo.list.assert_called_once()
        call_kwargs = txn_repo.list.call_args[1]
        passed_filters = call_kwargs["filters"]
        assert passed_filters.user_scope == staff_id

    @given(
        admin_id=st.uuids(),
        page=st.integers(min_value=1, max_value=10),
        page_size=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_admin_list_transactions_has_no_user_scope(
        self, admin_id: uuid.UUID, page: int, page_size: int
    ):
        """For any admin user listing transactions, the service does NOT set
        user_scope, allowing access to all transactions."""
        txn_repo = AsyncMock()
        product_repo = AsyncMock()

        # Create an admin user
        admin_user = _make_mock_user(user_id=admin_id, role=UserRole.admin)

        # Mock repo to return empty results
        txn_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        service = TransactionService(txn_repo=txn_repo, product_repo=product_repo)

        filters = TransactionFilters()
        pagination = PaginationParams(page=page, page_size=page_size)

        await service.list_transactions(
            user=admin_user, filters=filters, pagination=pagination
        )

        # Verify the repo was called without user_scope restriction
        txn_repo.list.assert_called_once()
        call_kwargs = txn_repo.list.call_args[1]
        passed_filters = call_kwargs["filters"]
        assert passed_filters.user_scope is None

    @given(
        staff_id=st.uuids(),
        other_cashier_id=st.uuids(),
        transaction_id=st.uuids(),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_staff_cannot_access_other_users_transaction(
        self, staff_id: uuid.UUID, other_cashier_id: uuid.UUID, transaction_id: uuid.UUID
    ):
        """For any staff user attempting to access a transaction belonging to
        another user, the service raises NotFoundException."""
        assume(staff_id != other_cashier_id)

        txn_repo = AsyncMock()
        product_repo = AsyncMock()

        staff_user = _make_mock_user(user_id=staff_id, role=UserRole.staff)

        # Transaction belongs to another cashier
        other_txn = _make_mock_transaction(
            transaction_id=transaction_id,
            cashier_id=other_cashier_id,
        )
        txn_repo.get_by_id.return_value = other_txn

        service = TransactionService(txn_repo=txn_repo, product_repo=product_repo)

        with pytest.raises(NotFoundException):
            await service.get_transaction(
                transaction_id=transaction_id, user=staff_user
            )

    @given(
        staff_id=st.uuids(),
        transaction_id=st.uuids(),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    @pytest.mark.asyncio
    async def test_staff_can_access_own_transaction(
        self, staff_id: uuid.UUID, transaction_id: uuid.UUID
    ):
        """For any staff user accessing their own transaction, the service
        returns the transaction successfully."""
        txn_repo = AsyncMock()
        product_repo = AsyncMock()

        staff_user = _make_mock_user(user_id=staff_id, role=UserRole.staff)

        # Transaction belongs to the same staff user
        own_txn = _make_mock_transaction(
            transaction_id=transaction_id,
            cashier_id=staff_id,
        )
        txn_repo.get_by_id.return_value = own_txn

        service = TransactionService(txn_repo=txn_repo, product_repo=product_repo)

        result = await service.get_transaction(
            transaction_id=transaction_id, user=staff_user
        )

        assert result is not None
        assert result.id == transaction_id
        assert result.cashier_id == staff_id

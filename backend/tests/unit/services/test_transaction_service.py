"""Unit tests for TransactionService."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.dependencies import PaginationParams
from app.core.exceptions import NotFoundException, ValidationException
from app.domain.interfaces import (
    PaginatedResult,
    ProductRepositoryInterface,
    TransactionFilters,
    TransactionRepositoryInterface,
)
from app.schemas.enums import DiscountType, PaymentMethod, UserRole
from app.services.transaction_service import (
    TransactionItemInput,
    TransactionReceipt,
    TransactionService,
)


# --- Helpers ---


def _make_product(
    product_id: Optional[uuid.UUID] = None,
    name: str = "Test Product",
    price: Decimal = Decimal("10.00"),
    stock: int = 50,
    is_active: bool = True,
) -> MagicMock:
    """Create a mock Product object."""
    product = MagicMock()
    product.id = product_id or uuid.uuid4()
    product.name = name
    product.price = price
    product.stock = stock
    product.is_active = is_active
    return product


def _make_user(
    user_id: Optional[uuid.UUID] = None,
    role: UserRole = UserRole.staff,
    full_name: str = "Test User",
) -> MagicMock:
    """Create a mock User object."""
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.role = role
    user.full_name = full_name
    return user


def _make_transaction(
    transaction_id: Optional[uuid.UUID] = None,
    cashier_id: Optional[uuid.UUID] = None,
    cashier_name: str = "Test Cashier",
    total_amount: Decimal = Decimal("100.00"),
    discount_amount: Decimal = Decimal("0.00"),
    payment_method: PaymentMethod = PaymentMethod.cash,
) -> MagicMock:
    """Create a mock Transaction object."""
    txn = MagicMock()
    txn.id = transaction_id or uuid.uuid4()
    txn.cashier_id = cashier_id or uuid.uuid4()
    txn.total_amount = total_amount
    txn.discount_amount = discount_amount
    txn.payment_method = payment_method
    txn.created_at = datetime.now(timezone.utc)
    txn.cashier = MagicMock()
    txn.cashier.full_name = cashier_name
    txn.items = []
    return txn


def _create_service(
    txn_repo: Optional[AsyncMock] = None,
    product_repo: Optional[AsyncMock] = None,
) -> TransactionService:
    """Create a TransactionService with mock repositories."""
    return TransactionService(
        txn_repo=txn_repo or AsyncMock(spec=TransactionRepositoryInterface),
        product_repo=product_repo or AsyncMock(spec=ProductRepositoryInterface),
    )


# --- Create Transaction Tests ---


class TestTransactionServiceCreateTransaction:
    """Tests for TransactionService.create_transaction()."""

    @pytest.mark.asyncio
    async def test_create_transaction_success(self) -> None:
        """Successful transaction creation returns a receipt."""
        product_id = uuid.uuid4()
        cashier_id = uuid.uuid4()
        product = _make_product(product_id=product_id, price=Decimal("25.00"), stock=10)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product

        txn = _make_transaction(
            cashier_id=cashier_id,
            total_amount=Decimal("50.00"),
            cashier_name="John Doe",
        )
        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.create.return_value = txn

        service = _create_service(txn_repo=txn_repo, product_repo=product_repo)

        result = await service.create_transaction(
            cashier_id=cashier_id,
            items=[TransactionItemInput(product_id=product_id, quantity=2)],
            payment_method=PaymentMethod.cash,
        )

        assert isinstance(result, TransactionReceipt)
        assert result.id == txn.id
        assert result.cashier_name == "John Doe"
        assert result.payment_method == PaymentMethod.cash
        assert len(result.items) == 1
        assert result.items[0].product_id == product_id
        assert result.items[0].quantity == 2
        assert result.items[0].unit_price == Decimal("25.00")
        assert result.items[0].subtotal == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_create_transaction_empty_items_raises(self) -> None:
        """Empty items list raises ValidationException."""
        service = _create_service()

        with pytest.raises(ValidationException) as exc_info:
            await service.create_transaction(
                cashier_id=uuid.uuid4(),
                items=[],
                payment_method=PaymentMethod.cash,
            )

        assert "at least one item" in exc_info.value.errors[0].detail.lower()

    @pytest.mark.asyncio
    async def test_create_transaction_product_not_found_raises(self) -> None:
        """Non-existent product raises ValidationException."""
        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = None

        service = _create_service(product_repo=product_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_transaction(
                cashier_id=uuid.uuid4(),
                items=[TransactionItemInput(product_id=uuid.uuid4(), quantity=1)],
                payment_method=PaymentMethod.cash,
            )

        assert "not found" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_create_transaction_inactive_product_raises(self) -> None:
        """Inactive product raises ValidationException."""
        product_id = uuid.uuid4()
        product = _make_product(product_id=product_id, is_active=False)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product

        service = _create_service(product_repo=product_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_transaction(
                cashier_id=uuid.uuid4(),
                items=[TransactionItemInput(product_id=product_id, quantity=1)],
                payment_method=PaymentMethod.cash,
            )

        assert "inactive" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_create_transaction_insufficient_stock_raises(self) -> None:
        """Insufficient stock raises ValidationException with product IDs."""
        product_id = uuid.uuid4()
        product = _make_product(product_id=product_id, stock=5)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product

        service = _create_service(product_repo=product_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_transaction(
                cashier_id=uuid.uuid4(),
                items=[TransactionItemInput(product_id=product_id, quantity=10)],
                payment_method=PaymentMethod.cash,
            )

        assert "insufficient stock" in exc_info.value.message.lower()
        assert str(product_id) in exc_info.value.errors[0].detail

    @pytest.mark.asyncio
    async def test_create_transaction_percentage_discount(self) -> None:
        """Percentage discount is correctly calculated."""
        product_id = uuid.uuid4()
        cashier_id = uuid.uuid4()
        product = _make_product(product_id=product_id, price=Decimal("100.00"), stock=10)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product

        txn = _make_transaction(
            cashier_id=cashier_id,
            total_amount=Decimal("90.00"),
            discount_amount=Decimal("10.00"),
        )
        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.create.return_value = txn

        service = _create_service(txn_repo=txn_repo, product_repo=product_repo)

        result = await service.create_transaction(
            cashier_id=cashier_id,
            items=[TransactionItemInput(product_id=product_id, quantity=1)],
            payment_method=PaymentMethod.cash,
            discount_type=DiscountType.percentage,
            discount_value=Decimal("10"),
        )

        # Verify the repo was called with correct amounts
        call_args = txn_repo.create.call_args
        assert call_args.kwargs["discount_amount"] == Decimal("10.00")
        assert call_args.kwargs["total_amount"] == Decimal("90.00")

    @pytest.mark.asyncio
    async def test_create_transaction_fixed_discount(self) -> None:
        """Fixed discount is correctly applied."""
        product_id = uuid.uuid4()
        cashier_id = uuid.uuid4()
        product = _make_product(product_id=product_id, price=Decimal("50.00"), stock=10)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product

        txn = _make_transaction(
            cashier_id=cashier_id,
            total_amount=Decimal("45.00"),
            discount_amount=Decimal("5.00"),
        )
        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.create.return_value = txn

        service = _create_service(txn_repo=txn_repo, product_repo=product_repo)

        result = await service.create_transaction(
            cashier_id=cashier_id,
            items=[TransactionItemInput(product_id=product_id, quantity=1)],
            payment_method=PaymentMethod.qris,
            discount_type=DiscountType.fixed,
            discount_value=Decimal("5.00"),
        )

        call_args = txn_repo.create.call_args
        assert call_args.kwargs["discount_amount"] == Decimal("5.00")
        assert call_args.kwargs["total_amount"] == Decimal("45.00")

    @pytest.mark.asyncio
    async def test_create_transaction_discount_exceeds_subtotal_raises(self) -> None:
        """Discount exceeding subtotal raises ValidationException."""
        product_id = uuid.uuid4()
        product = _make_product(product_id=product_id, price=Decimal("10.00"), stock=10)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product

        service = _create_service(product_repo=product_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_transaction(
                cashier_id=uuid.uuid4(),
                items=[TransactionItemInput(product_id=product_id, quantity=1)],
                payment_method=PaymentMethod.cash,
                discount_type=DiscountType.fixed,
                discount_value=Decimal("20.00"),
            )

        assert "exceed" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_create_transaction_percentage_over_100_raises(self) -> None:
        """Percentage discount over 100% raises ValidationException."""
        product_id = uuid.uuid4()
        product = _make_product(product_id=product_id, price=Decimal("10.00"), stock=10)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)
        product_repo.get_by_id.return_value = product

        service = _create_service(product_repo=product_repo)

        with pytest.raises(ValidationException) as exc_info:
            await service.create_transaction(
                cashier_id=uuid.uuid4(),
                items=[TransactionItemInput(product_id=product_id, quantity=1)],
                payment_method=PaymentMethod.cash,
                discount_type=DiscountType.percentage,
                discount_value=Decimal("150"),
            )

        assert "percentage" in exc_info.value.errors[0].detail.lower()

    @pytest.mark.asyncio
    async def test_create_transaction_multiple_items(self) -> None:
        """Transaction with multiple items calculates correct subtotal."""
        product_a_id = uuid.uuid4()
        product_b_id = uuid.uuid4()
        cashier_id = uuid.uuid4()

        product_a = _make_product(product_id=product_a_id, name="Product A", price=Decimal("10.00"), stock=20)
        product_b = _make_product(product_id=product_b_id, name="Product B", price=Decimal("25.00"), stock=15)

        product_repo = AsyncMock(spec=ProductRepositoryInterface)

        async def get_by_id_side_effect(pid: uuid.UUID):
            if pid == product_a_id:
                return product_a
            elif pid == product_b_id:
                return product_b
            return None

        product_repo.get_by_id.side_effect = get_by_id_side_effect

        txn = _make_transaction(
            cashier_id=cashier_id,
            total_amount=Decimal("70.00"),
        )
        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.create.return_value = txn

        service = _create_service(txn_repo=txn_repo, product_repo=product_repo)

        result = await service.create_transaction(
            cashier_id=cashier_id,
            items=[
                TransactionItemInput(product_id=product_a_id, quantity=2),
                TransactionItemInput(product_id=product_b_id, quantity=2),
            ],
            payment_method=PaymentMethod.debit_card,
        )

        # Subtotal should be (2*10) + (2*25) = 70
        call_args = txn_repo.create.call_args
        assert call_args.kwargs["total_amount"] == Decimal("70.00")
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_create_transaction_all_payment_methods(self) -> None:
        """All payment methods are accepted."""
        for method in PaymentMethod:
            product_id = uuid.uuid4()
            cashier_id = uuid.uuid4()
            product = _make_product(product_id=product_id, stock=10)

            product_repo = AsyncMock(spec=ProductRepositoryInterface)
            product_repo.get_by_id.return_value = product

            txn = _make_transaction(cashier_id=cashier_id, payment_method=method)
            txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
            txn_repo.create.return_value = txn

            service = _create_service(txn_repo=txn_repo, product_repo=product_repo)

            result = await service.create_transaction(
                cashier_id=cashier_id,
                items=[TransactionItemInput(product_id=product_id, quantity=1)],
                payment_method=method,
            )

            assert result.payment_method == method


# --- List Transactions Tests ---


class TestTransactionServiceListTransactions:
    """Tests for TransactionService.list_transactions()."""

    @pytest.mark.asyncio
    async def test_list_transactions_staff_scoped(self) -> None:
        """Staff user sees only their own transactions."""
        user = _make_user(role=UserRole.staff)
        filters = TransactionFilters()
        pagination = PaginationParams(page=1, page_size=20)

        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        service = _create_service(txn_repo=txn_repo)

        await service.list_transactions(user=user, filters=filters, pagination=pagination)

        # Verify user_scope was set to the staff user's ID
        call_args = txn_repo.list.call_args
        assert call_args.kwargs["filters"].user_scope == user.id

    @pytest.mark.asyncio
    async def test_list_transactions_admin_no_scope(self) -> None:
        """Admin user sees all transactions (no user_scope)."""
        user = _make_user(role=UserRole.admin)
        filters = TransactionFilters()
        pagination = PaginationParams(page=1, page_size=20)

        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        service = _create_service(txn_repo=txn_repo)

        await service.list_transactions(user=user, filters=filters, pagination=pagination)

        # Verify user_scope was NOT set for admin
        call_args = txn_repo.list.call_args
        assert call_args.kwargs["filters"].user_scope is None

    @pytest.mark.asyncio
    async def test_list_transactions_pagination_passed_through(self) -> None:
        """Pagination parameters are passed to the repository."""
        user = _make_user(role=UserRole.admin)
        filters = TransactionFilters()
        pagination = PaginationParams(page=3, page_size=50)

        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.list.return_value = PaginatedResult(items=[], total_count=0)

        service = _create_service(txn_repo=txn_repo)

        await service.list_transactions(user=user, filters=filters, pagination=pagination)

        call_args = txn_repo.list.call_args
        assert call_args.kwargs["pagination"].page == 3
        assert call_args.kwargs["pagination"].page_size == 50


# --- Get Transaction Tests ---


class TestTransactionServiceGetTransaction:
    """Tests for TransactionService.get_transaction()."""

    @pytest.mark.asyncio
    async def test_get_transaction_admin_success(self) -> None:
        """Admin can access any transaction."""
        user = _make_user(role=UserRole.admin)
        txn_id = uuid.uuid4()
        txn = _make_transaction(transaction_id=txn_id, cashier_id=uuid.uuid4())

        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.get_by_id.return_value = txn

        service = _create_service(txn_repo=txn_repo)

        result = await service.get_transaction(transaction_id=txn_id, user=user)
        assert result.id == txn_id

    @pytest.mark.asyncio
    async def test_get_transaction_staff_own_success(self) -> None:
        """Staff can access their own transaction."""
        user = _make_user(role=UserRole.staff)
        txn_id = uuid.uuid4()
        txn = _make_transaction(transaction_id=txn_id, cashier_id=user.id)

        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.get_by_id.return_value = txn

        service = _create_service(txn_repo=txn_repo)

        result = await service.get_transaction(transaction_id=txn_id, user=user)
        assert result.id == txn_id

    @pytest.mark.asyncio
    async def test_get_transaction_staff_other_raises(self) -> None:
        """Staff cannot access another user's transaction."""
        user = _make_user(role=UserRole.staff)
        txn_id = uuid.uuid4()
        txn = _make_transaction(transaction_id=txn_id, cashier_id=uuid.uuid4())

        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.get_by_id.return_value = txn

        service = _create_service(txn_repo=txn_repo)

        with pytest.raises(NotFoundException):
            await service.get_transaction(transaction_id=txn_id, user=user)

    @pytest.mark.asyncio
    async def test_get_transaction_not_found_raises(self) -> None:
        """Non-existent transaction raises NotFoundException."""
        user = _make_user(role=UserRole.admin)

        txn_repo = AsyncMock(spec=TransactionRepositoryInterface)
        txn_repo.get_by_id.return_value = None

        service = _create_service(txn_repo=txn_repo)

        with pytest.raises(NotFoundException):
            await service.get_transaction(transaction_id=uuid.uuid4(), user=user)

"""Transaction API routes.

Provides POS transaction endpoints:
- POST / : Create a new transaction (any authenticated user)
- GET / : List transactions scoped by role (staff=own, admin=all with filters)
- GET /{transaction_id} : Get a single transaction scoped by role
"""

import math
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    PaginationParams,
    get_current_user,
    get_pagination,
)
from app.domain.interfaces import TransactionFilters
from app.models.user import User
from app.repositories.product_repository import ProductRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.common import APIResponse, PaginatedMeta, PaginatedResponse
from app.schemas.enums import PaymentMethod, UserRole
from app.schemas.transaction import (
    ReceiptItemResponse,
    TransactionCreate,
    TransactionReceiptResponse,
    TransactionResponse,
)
from app.services.transaction_service import TransactionItemInput, TransactionService

router = APIRouter()


async def _get_db_session():  # type: ignore[no-untyped-def]
    """Lazy wrapper for get_db_session to avoid circular imports at module level."""
    from app.infrastructure.database import get_db_session

    async for session in get_db_session():
        yield session


def _get_transaction_service(session: AsyncSession) -> TransactionService:
    """Construct a TransactionService with required repository dependencies.

    Args:
        session: The async database session for the current request.

    Returns:
        A fully-initialized TransactionService instance.
    """
    txn_repo = TransactionRepository(session)
    product_repo = ProductRepository(session)
    return TransactionService(txn_repo=txn_repo, product_repo=product_repo)


@router.post("/", response_model=APIResponse[TransactionReceiptResponse], status_code=201)
async def create_transaction(
    body: TransactionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[TransactionReceiptResponse]:
    """Create a new transaction.

    Authenticated (any role). Validates stock availability and discount.
    Returns a complete receipt on success.

    Returns 400 for insufficient stock or invalid discount.
    """
    txn_service = _get_transaction_service(session)

    # Convert schema items to service input
    items = [
        TransactionItemInput(product_id=item.product_id, quantity=item.quantity)
        for item in body.items
    ]

    receipt = await txn_service.create_transaction(
        cashier_id=current_user.id,
        items=items,
        payment_method=body.payment_method,
        discount_type=body.discount_type,
        discount_value=body.discount_value,
    )

    await session.commit()

    # Convert service receipt to response schema
    receipt_items = [
        ReceiptItemResponse(
            product_id=item.product_id,
            product_name=item.product_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.subtotal,
        )
        for item in receipt.items
    ]

    receipt_response = TransactionReceiptResponse(
        id=receipt.id,
        items=receipt_items,
        total_amount=receipt.total_amount,
        discount_amount=receipt.discount_amount,
        payment_method=receipt.payment_method,
        cashier_name=receipt.cashier_name,
        created_at=receipt.created_at,
    )

    return APIResponse(
        success=True,
        data=receipt_response,
        message="Transaction created successfully",
    )


@router.get("/", response_model=PaginatedResponse[TransactionResponse])
async def list_transactions(
    cashier_id: Optional[uuid.UUID] = Query(None, description="Filter by cashier ID (admin only)"),
    payment_method: Optional[PaymentMethod] = Query(None, description="Filter by payment method"),
    date_from: Optional[datetime] = Query(None, description="Filter transactions from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter transactions until this date"),
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(_get_db_session),
) -> PaginatedResponse[TransactionResponse]:
    """List transactions with role-scoped access.

    Staff users see only their own transactions.
    Admin users see all transactions with optional filters.
    """
    txn_service = _get_transaction_service(session)

    # Build filters - cashier_id filter only applies for admin users
    filters = TransactionFilters(
        cashier_id=cashier_id if current_user.role == UserRole.admin else None,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
    )

    result = await txn_service.list_transactions(
        user=current_user,
        filters=filters,
        pagination=pagination,
    )

    transaction_responses = [
        TransactionResponse.model_validate(txn) for txn in result.items
    ]

    total_pages = (
        math.ceil(result.total_count / pagination.page_size)
        if result.total_count > 0
        else 0
    )

    return PaginatedResponse(
        success=True,
        data=transaction_responses,
        message="Transactions retrieved successfully",
        meta=PaginatedMeta(
            total_count=result.total_count,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=total_pages,
        ),
    )


@router.get("/{transaction_id}", response_model=APIResponse[TransactionResponse])
async def get_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[TransactionResponse]:
    """Get a single transaction by ID.

    Staff users can only access their own transactions.
    Admin users can access any transaction.
    Returns 404 if transaction not found or user lacks access.
    """
    txn_service = _get_transaction_service(session)

    transaction = await txn_service.get_transaction(
        transaction_id=transaction_id,
        user=current_user,
    )

    transaction_response = TransactionResponse.model_validate(transaction)

    return APIResponse(
        success=True,
        data=transaction_response,
        message="Transaction retrieved successfully",
    )

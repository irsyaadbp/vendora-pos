"""Dashboard API route.

Provides the admin dashboard endpoint:
- GET / : Retrieve aggregated business metrics (admin only)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_admin
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.dashboard import DashboardResponse

router = APIRouter()


async def _get_db_session():  # type: ignore[no-untyped-def]
    """Lazy wrapper for get_db_session to avoid circular imports at module level."""
    from app.infrastructure.database import get_db_session

    async for session in get_db_session():
        yield session


@router.get("/", response_model=APIResponse[DashboardResponse])
async def get_dashboard(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(_get_db_session),
) -> APIResponse[DashboardResponse]:
    """Retrieve aggregated dashboard metrics for the admin overview.

    Requires admin role. Returns today's sales, transaction count,
    low-stock products, active staff count, and recent transactions.
    Returns 403 for non-admin access.
    """
    from app.core.config import get_settings
    from app.repositories.product_repository import ProductRepository
    from app.repositories.transaction_repository import TransactionRepository
    from app.repositories.user_repository import UserRepository
    from app.services.dashboard_service import DashboardService

    settings = get_settings()
    transaction_repo = TransactionRepository(session)
    product_repo = ProductRepository(session)
    user_repo = UserRepository(session)

    dashboard_service = DashboardService(
        txn_repo=transaction_repo,
        product_repo=product_repo,
        user_repo=user_repo,
        settings=settings,
    )

    metrics = await dashboard_service.get_dashboard_metrics()

    return APIResponse(
        success=True,
        data=metrics,
        message="Dashboard metrics retrieved successfully",
    )

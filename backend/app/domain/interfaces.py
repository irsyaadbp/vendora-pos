"""Abstract repository interfaces for the domain layer.

Defines contracts that repository implementations must fulfill,
enabling dependency inversion and testability.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from app.core.dependencies import PaginationParams
from app.models.category import Category
from app.models.inventory_log import InventoryLog
from app.models.login_attempt import LoginAttempt
from app.models.product import Product
from app.models.refresh_token import RefreshToken
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.enums import AdjustmentType, PaymentMethod, UserRole


class PaginatedResult:
    """Container for paginated query results."""

    def __init__(self, items: list, total_count: int) -> None:
        self.items = items
        self.total_count = total_count


class UserFilters:
    """Filters for user list queries."""

    def __init__(
        self,
        search: Optional[str] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> None:
        self.search = search
        self.role = role
        self.is_active = is_active


class UserRepositoryInterface(ABC):
    """Abstract interface for user data access operations."""

    @abstractmethod
    async def create(
        self,
        full_name: str,
        email: str,
        password_hash: str,
        role: UserRole,
    ) -> User:
        """Create a new user record.

        Args:
            full_name: User's full name.
            email: User's email address (must be unique).
            password_hash: Bcrypt-hashed password.
            role: User role (admin or staff).

        Returns:
            The created User instance.
        """
        ...

    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Retrieve a user by their unique identifier.

        Args:
            user_id: The UUID of the user.

        Returns:
            The User instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Retrieve a user by their email address.

        Args:
            email: The email address to look up.

        Returns:
            The User instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def update(
        self,
        user_id: uuid.UUID,
        **kwargs: object,
    ) -> Optional[User]:
        """Update a user's fields.

        Args:
            user_id: The UUID of the user to update.
            **kwargs: Fields to update (full_name, email, role, is_active, password_hash).

        Returns:
            The updated User instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def list(
        self,
        filters: UserFilters,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """List users with filtering and pagination.

        Args:
            filters: Filtering criteria (search, role, is_active).
            pagination: Pagination parameters (page, page_size).

        Returns:
            PaginatedResult containing matching users and total count.
        """
        ...


class RefreshTokenRepositoryInterface(ABC):
    """Abstract interface for refresh token data access operations."""

    @abstractmethod
    async def create(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        token_family: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Store a new refresh token record.

        Args:
            user_id: The UUID of the token owner.
            token_hash: Hashed refresh token value.
            token_family: Token family identifier for rotation tracking.
            expires_at: Token expiration timestamp.

        Returns:
            The created RefreshToken instance.
        """
        ...

    @abstractmethod
    async def get_by_token_hash(self, token_hash: str) -> Optional[RefreshToken]:
        """Retrieve a refresh token by its hash.

        Args:
            token_hash: The hashed token value to look up.

        Returns:
            The RefreshToken instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def revoke(self, token_id: uuid.UUID) -> None:
        """Revoke a single refresh token.

        Args:
            token_id: The UUID of the token to revoke.
        """
        ...

    @abstractmethod
    async def revoke_family(self, token_family: str) -> None:
        """Revoke all refresh tokens in a token family.

        Used when token reuse is detected to invalidate the entire family.

        Args:
            token_family: The token family identifier.
        """
        ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke all refresh tokens for a specific user.

        Used when a user is deactivated or compromised.

        Args:
            user_id: The UUID of the user whose tokens should be revoked.
        """
        ...


class LoginAttemptRepositoryInterface(ABC):
    """Abstract interface for login attempt tracking operations."""

    @abstractmethod
    async def create(
        self,
        user_id: uuid.UUID,
        success: bool,
    ) -> LoginAttempt:
        """Record a login attempt.

        Args:
            user_id: The UUID of the user who attempted login.
            success: Whether the login attempt was successful.

        Returns:
            The created LoginAttempt instance.
        """
        ...

    @abstractmethod
    async def get_recent_failures(
        self,
        user_id: uuid.UUID,
        since: datetime,
    ) -> list[LoginAttempt]:
        """Get recent failed login attempts for lockout checking.

        Args:
            user_id: The UUID of the user.
            since: Only return attempts after this timestamp.

        Returns:
            List of failed LoginAttempt instances since the given time.
        """
        ...


class ProductFilters:
    """Filters for product search queries."""

    def __init__(
        self,
        category_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
    ) -> None:
        self.category_id = category_id
        self.is_active = is_active


class ProductRepositoryInterface(ABC):
    """Abstract interface for product data access operations."""

    @abstractmethod
    async def create(
        self,
        name: str,
        sku: str,
        price: object,
        stock: int,
        barcode: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
    ) -> Product:
        """Create a new product record.

        Args:
            name: Product name.
            sku: Stock Keeping Unit (must be unique).
            price: Product price (Decimal).
            stock: Initial stock quantity.
            barcode: Optional barcode (must be unique if provided).
            category_id: Optional category UUID.

        Returns:
            The created Product instance.
        """
        ...

    @abstractmethod
    async def get_by_id(self, product_id: uuid.UUID) -> Optional[Product]:
        """Retrieve a product by its unique identifier.

        Args:
            product_id: The UUID of the product.

        Returns:
            The Product instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Retrieve a product by its SKU.

        Args:
            sku: The SKU to look up.

        Returns:
            The Product instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def get_by_barcode(self, barcode: str) -> Optional[Product]:
        """Retrieve a product by its barcode.

        Args:
            barcode: The barcode to look up.

        Returns:
            The Product instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def search(
        self,
        query: Optional[str],
        filters: ProductFilters,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """Search products with partial name matching and exact SKU/barcode matching.

        Performs partial matching (ilike) on name, exact matching on SKU and barcode.
        Only returns active products by default.

        Args:
            query: Search query string (partial name, exact SKU, or exact barcode).
            filters: Filtering criteria (category_id, is_active).
            pagination: Pagination parameters (page, page_size).

        Returns:
            PaginatedResult containing matching products and total count.
        """
        ...

    @abstractmethod
    async def update(
        self,
        product_id: uuid.UUID,
        **kwargs: object,
    ) -> Optional[Product]:
        """Update a product's fields.

        Args:
            product_id: The UUID of the product to update.
            **kwargs: Fields to update (name, sku, barcode, price, stock, category_id, is_active).

        Returns:
            The updated Product instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def update_stock(
        self,
        product_id: uuid.UUID,
        quantity_change: int,
    ) -> Optional[Product]:
        """Update a product's stock by a relative quantity change.

        Args:
            product_id: The UUID of the product.
            quantity_change: The amount to add (positive) or subtract (negative).

        Returns:
            The updated Product instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def get_low_stock(
        self,
        threshold: int,
        pagination: PaginationParams,
    ) -> "PaginatedResult":
        """Retrieve active products with stock at or below the given threshold.

        Args:
            threshold: The stock level threshold (inclusive).
            pagination: Pagination parameters (page, page_size).

        Returns:
            PaginatedResult containing low-stock products and total count.
        """
        ...


class CategoryRepositoryInterface(ABC):
    """Abstract interface for category data access operations."""

    @abstractmethod
    async def create(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> Category:
        """Create a new category record.

        Args:
            name: Category name (must be unique).
            description: Optional category description.

        Returns:
            The created Category instance.
        """
        ...

    @abstractmethod
    async def get_by_id(self, category_id: uuid.UUID) -> Optional[Category]:
        """Retrieve a category by its unique identifier.

        Args:
            category_id: The UUID of the category.

        Returns:
            The Category instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Category]:
        """Retrieve a category by its name.

        Args:
            name: The category name to look up.

        Returns:
            The Category instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def list(
        self,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """List categories with pagination.

        Args:
            pagination: Pagination parameters (page, page_size).

        Returns:
            PaginatedResult containing categories and total count.
        """
        ...

    @abstractmethod
    async def update(
        self,
        category_id: uuid.UUID,
        **kwargs: object,
    ) -> Optional[Category]:
        """Update a category's fields.

        Args:
            category_id: The UUID of the category to update.
            **kwargs: Fields to update (name, description).

        Returns:
            The updated Category instance if found, None otherwise.
        """
        ...

    @abstractmethod
    async def delete(self, category_id: uuid.UUID) -> None:
        """Delete a category by its ID.

        Args:
            category_id: The UUID of the category to delete.
        """
        ...


class TransactionFilters:
    """Filters for transaction list queries."""

    def __init__(
        self,
        cashier_id: Optional[uuid.UUID] = None,
        payment_method: Optional[PaymentMethod] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        user_scope: Optional[uuid.UUID] = None,
    ) -> None:
        """Initialize transaction filters.

        Args:
            cashier_id: Filter by specific cashier (admin filter).
            payment_method: Filter by payment method.
            date_from: Filter transactions created on or after this datetime.
            date_to: Filter transactions created on or before this datetime.
            user_scope: If set, restricts results to this user's transactions
                        (used for staff role-scoped access).
        """
        self.cashier_id = cashier_id
        self.payment_method = payment_method
        self.date_from = date_from
        self.date_to = date_to
        self.user_scope = user_scope


class TransactionRepositoryInterface(ABC):
    """Abstract interface for transaction data access operations."""

    @abstractmethod
    async def create(
        self,
        cashier_id: uuid.UUID,
        total_amount: object,
        discount_amount: object,
        payment_method: PaymentMethod,
        items: list[dict],
    ) -> Transaction:
        """Atomically create a transaction with items and decrement stock.

        This operation must be performed within a single database transaction:
        1. Validate stock availability for all items
        2. Insert the transaction record
        3. Insert all transaction item records
        4. Decrement product stock for each item

        Args:
            cashier_id: UUID of the cashier processing the transaction.
            total_amount: Total transaction amount (Decimal).
            discount_amount: Discount applied (Decimal).
            payment_method: Payment method used.
            items: List of dicts with keys: product_id, quantity, unit_price, subtotal.

        Returns:
            The created Transaction instance with items loaded.

        Raises:
            ValueError: If any product has insufficient stock.
        """
        ...

    @abstractmethod
    async def get_by_id(self, transaction_id: uuid.UUID) -> Optional[Transaction]:
        """Retrieve a transaction by its unique identifier.

        Args:
            transaction_id: The UUID of the transaction.

        Returns:
            The Transaction instance with items if found, None otherwise.
        """
        ...

    @abstractmethod
    async def list(
        self,
        filters: "TransactionFilters",
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """List transactions with filtering and pagination.

        Supports role-scoped filtering via user_scope in filters:
        - If user_scope is set, only returns that user's transactions (staff).
        - If user_scope is None, returns all transactions (admin).

        Additional filters: cashier_id, payment_method, date_from, date_to.

        Args:
            filters: TransactionFilters with optional criteria.
            pagination: Pagination parameters (page, page_size).

        Returns:
            PaginatedResult containing matching transactions and total count.
        """
        ...


class InventoryLogRepositoryInterface(ABC):
    """Abstract interface for inventory log data access operations."""

    @abstractmethod
    async def create(
        self,
        product_id: uuid.UUID,
        user_id: uuid.UUID,
        adjustment_type: AdjustmentType,
        quantity_change: int,
        reason: Optional[str] = None,
    ) -> InventoryLog:
        """Create a new inventory log entry.

        Args:
            product_id: The UUID of the product being adjusted.
            user_id: The UUID of the user performing the adjustment.
            adjustment_type: The type of adjustment (stock_in, stock_out, adjustment).
            quantity_change: The quantity change (positive for stock_in, negative for stock_out).
            reason: Optional reason for the adjustment (required for adjustments).

        Returns:
            The created InventoryLog instance.
        """
        ...

    @abstractmethod
    async def list_by_product(
        self,
        product_id: uuid.UUID,
        pagination: PaginationParams,
    ) -> PaginatedResult:
        """List inventory logs for a specific product with pagination.

        Results are sorted by created_at descending (most recent first).

        Args:
            product_id: The UUID of the product to get logs for.
            pagination: Pagination parameters (page, page_size).

        Returns:
            PaginatedResult containing inventory logs and total count.
        """
        ...

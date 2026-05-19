"""Property-based tests for database model constraints.

Feature: vendora-pos-foundation
Property 12: Email uniqueness constraint
Property 16: Product SKU and barcode uniqueness

Validates: Requirements 2.2, 2.3, 5.2, 6.2, 6.3, 6.4

These tests verify that the SQLAlchemy model metadata correctly defines
unique constraints on email, SKU, and barcode columns without requiring
a live database connection.
"""

from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import inspect

from app.models.product import Product
from app.models.user import User


# --- Strategies ---

email_strategy = st.emails()

sku_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=100,
)

barcode_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("N",)),
    min_size=1,
    max_size=100,
)

full_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "Zs")),
    min_size=1,
    max_size=100,
).filter(lambda x: x.strip() != "")

product_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Zs")),
    min_size=1,
    max_size=255,
).filter(lambda x: x.strip() != "")

price_strategy = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("999999999.99"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

stock_strategy = st.integers(min_value=0, max_value=999999)


# --- Property 12: Email uniqueness constraint ---


class TestEmailUniquenessConstraint:
    """**Validates: Requirements 2.2, 5.2**

    Property 12: For any two user records in the system, their email
    addresses SHALL be distinct. The User model has a unique constraint
    on the email column.
    """

    def test_user_email_column_has_unique_constraint(self):
        """Verify the email column on the User model is marked unique=True
        at the SQLAlchemy metadata level."""
        mapper = inspect(User)
        email_col = mapper.columns["email"]
        assert email_col.unique is True, (
            "User.email column must have unique=True"
        )

    def test_user_email_column_has_index(self):
        """Verify the email column on the User model is indexed."""
        mapper = inspect(User)
        email_col = mapper.columns["email"]
        assert email_col.index is True, (
            "User.email column must have index=True"
        )

    @given(email=email_strategy, full_name=full_name_strategy)
    @settings(max_examples=100)
    def test_user_model_instantiation_with_random_email(
        self, email: str, full_name: str
    ):
        """For any valid email and full_name, the User model can be
        instantiated and the email attribute is correctly stored."""
        user = User(
            full_name=full_name,
            email=email,
            password_hash="$2b$12$fakehashvalue",
            role="admin",
            is_active=True,
        )
        assert user.email == email
        assert user.full_name == full_name

    @given(email=email_strategy)
    @settings(max_examples=100)
    def test_email_unique_constraint_defined_in_table_metadata(
        self, email: str
    ):
        """For any email value, the users table metadata confirms the
        unique constraint exists on the email column."""
        table = User.__table__
        email_col = table.c.email
        assert email_col.unique is True, (
            f"For email '{email}', the users table must enforce uniqueness "
            "at the schema level"
        )


# --- Property 16: Product SKU and barcode uniqueness ---


class TestProductSKUUniquenessConstraint:
    """**Validates: Requirements 2.3, 6.2, 6.3**

    Property 16: For any two active products in the system, their SKU
    values SHALL be distinct. The Product model has a unique constraint
    on the SKU column.
    """

    def test_product_sku_column_has_unique_constraint(self):
        """Verify the sku column on the Product model is marked unique=True
        at the SQLAlchemy metadata level."""
        mapper = inspect(Product)
        sku_col = mapper.columns["sku"]
        assert sku_col.unique is True, (
            "Product.sku column must have unique=True"
        )

    def test_product_sku_column_has_index(self):
        """Verify the sku column on the Product model is indexed."""
        mapper = inspect(Product)
        sku_col = mapper.columns["sku"]
        assert sku_col.index is True, (
            "Product.sku column must have index=True"
        )

    @given(sku=sku_strategy, name=product_name_strategy, price=price_strategy, stock=stock_strategy)
    @settings(max_examples=100)
    def test_product_model_instantiation_with_random_sku(
        self, sku: str, name: str, price: Decimal, stock: int
    ):
        """For any valid SKU, name, price, and stock, the Product model
        can be instantiated and the sku attribute is correctly stored."""
        product = Product(
            name=name,
            sku=sku,
            price=price,
            stock=stock,
            is_active=True,
        )
        assert product.sku == sku
        assert product.name == name
        assert product.price == price
        assert product.stock == stock

    @given(sku=sku_strategy)
    @settings(max_examples=100)
    def test_sku_unique_constraint_defined_in_table_metadata(self, sku: str):
        """For any SKU value, the products table metadata confirms the
        unique constraint exists on the sku column."""
        table = Product.__table__
        sku_col = table.c.sku
        assert sku_col.unique is True, (
            f"For SKU '{sku}', the products table must enforce uniqueness "
            "at the schema level"
        )


class TestProductBarcodeUniquenessConstraint:
    """**Validates: Requirements 2.3, 6.4**

    Property 16: For any two products with non-null barcodes, their
    barcode values SHALL be distinct. The Product model has a unique
    constraint on the barcode column.
    """

    def test_product_barcode_column_has_unique_constraint(self):
        """Verify the barcode column on the Product model is marked
        unique=True at the SQLAlchemy metadata level."""
        mapper = inspect(Product)
        barcode_col = mapper.columns["barcode"]
        assert barcode_col.unique is True, (
            "Product.barcode column must have unique=True"
        )

    def test_product_barcode_column_is_nullable(self):
        """Verify the barcode column on the Product model is nullable."""
        mapper = inspect(Product)
        barcode_col = mapper.columns["barcode"]
        assert barcode_col.nullable is True, (
            "Product.barcode column must be nullable"
        )

    def test_product_barcode_column_has_index(self):
        """Verify the barcode column on the Product model is indexed."""
        mapper = inspect(Product)
        barcode_col = mapper.columns["barcode"]
        assert barcode_col.index is True, (
            "Product.barcode column must have index=True"
        )

    @given(barcode=barcode_strategy, sku=sku_strategy, name=product_name_strategy)
    @settings(max_examples=100)
    def test_product_model_instantiation_with_random_barcode(
        self, barcode: str, sku: str, name: str
    ):
        """For any valid barcode, the Product model can be instantiated
        and the barcode attribute is correctly stored."""
        product = Product(
            name=name,
            sku=sku,
            barcode=barcode,
            price=Decimal("9.99"),
            stock=10,
            is_active=True,
        )
        assert product.barcode == barcode

    @given(barcode=barcode_strategy)
    @settings(max_examples=100)
    def test_barcode_unique_constraint_defined_in_table_metadata(
        self, barcode: str
    ):
        """For any barcode value, the products table metadata confirms
        the unique constraint exists on the barcode column."""
        table = Product.__table__
        barcode_col = table.c.barcode
        assert barcode_col.unique is True, (
            f"For barcode '{barcode}', the products table must enforce "
            "uniqueness at the schema level"
        )

    @given(sku=sku_strategy, name=product_name_strategy)
    @settings(max_examples=100)
    def test_product_model_instantiation_with_null_barcode(
        self, sku: str, name: str
    ):
        """For any product without a barcode, the model can be instantiated
        with barcode=None."""
        product = Product(
            name=name,
            sku=sku,
            barcode=None,
            price=Decimal("9.99"),
            stock=10,
            is_active=True,
        )
        assert product.barcode is None

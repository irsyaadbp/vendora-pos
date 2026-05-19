"""Shared enum types used across the application schemas and models."""

from enum import Enum


class UserRole(str, Enum):
    """User roles for RBAC authorization."""

    admin = "admin"
    staff = "staff"


class PaymentMethod(str, Enum):
    """Supported payment methods for transactions."""

    cash = "cash"
    qris = "qris"
    debit_card = "debit_card"
    credit_card = "credit_card"


class TransactionStatus(str, Enum):
    """Transaction lifecycle statuses."""

    completed = "completed"
    voided = "voided"


class AdjustmentType(str, Enum):
    """Inventory adjustment operation types."""

    stock_in = "stock_in"
    stock_out = "stock_out"
    adjustment = "adjustment"


class DiscountType(str, Enum):
    """Discount calculation types for transactions."""

    percentage = "percentage"
    fixed = "fixed"

"""Unit tests for Pydantic response schemas and enum types."""

import json

import pytest
from pydantic import ValidationError

from app.schemas.common import (
    APIErrorResponse,
    APIResponse,
    FieldError,
    PaginatedMeta,
    PaginatedResponse,
)
from app.schemas.enums import (
    AdjustmentType,
    PaymentMethod,
    TransactionStatus,
    UserRole,
)


class TestUserRole:
    def test_admin_value(self):
        assert UserRole.admin == "admin"

    def test_staff_value(self):
        assert UserRole.staff == "staff"

    def test_is_string_enum(self):
        assert isinstance(UserRole.admin, str)


class TestPaymentMethod:
    def test_cash_value(self):
        assert PaymentMethod.cash == "cash"

    def test_qris_value(self):
        assert PaymentMethod.qris == "qris"

    def test_debit_card_value(self):
        assert PaymentMethod.debit_card == "debit_card"

    def test_credit_card_value(self):
        assert PaymentMethod.credit_card == "credit_card"

    def test_has_four_members(self):
        assert len(PaymentMethod) == 4


class TestTransactionStatus:
    def test_completed_value(self):
        assert TransactionStatus.completed == "completed"

    def test_voided_value(self):
        assert TransactionStatus.voided == "voided"


class TestAdjustmentType:
    def test_stock_in_value(self):
        assert AdjustmentType.stock_in == "stock_in"

    def test_stock_out_value(self):
        assert AdjustmentType.stock_out == "stock_out"

    def test_adjustment_value(self):
        assert AdjustmentType.adjustment == "adjustment"


class TestFieldError:
    def test_creation(self):
        error = FieldError(field="email", detail="Invalid email format")
        assert error.field == "email"
        assert error.detail == "Invalid email format"

    def test_serialization(self):
        error = FieldError(field="password", detail="Too short")
        data = error.model_dump()
        assert data == {"field": "password", "detail": "Too short"}


class TestAPIResponse:
    def test_success_response_with_data(self):
        resp = APIResponse[dict](success=True, data={"id": "abc"}, message="Created")
        assert resp.success is True
        assert resp.data == {"id": "abc"}
        assert resp.message == "Created"

    def test_success_response_defaults(self):
        resp = APIResponse[dict]()
        assert resp.success is True
        assert resp.data is None
        assert resp.message == "Success"

    def test_json_format(self):
        resp = APIResponse[dict](success=True, data={"name": "Test"}, message="OK")
        data = json.loads(resp.model_dump_json())
        assert data == {"success": True, "data": {"name": "Test"}, "message": "OK"}

    def test_with_list_data(self):
        resp = APIResponse[list](data=[1, 2, 3], message="Found")
        assert resp.data == [1, 2, 3]

    def test_with_none_data(self):
        resp = APIResponse[dict](data=None, message="No content")
        assert resp.data is None


class TestAPIErrorResponse:
    def test_error_response(self):
        err = APIErrorResponse(
            message="Validation failed",
            errors=[FieldError(field="email", detail="Required")],
        )
        assert err.success is False
        assert err.data is None
        assert err.message == "Validation failed"
        assert len(err.errors) == 1

    def test_error_response_defaults(self):
        err = APIErrorResponse(message="Something went wrong")
        assert err.success is False
        assert err.data is None
        assert err.errors == []

    def test_json_format(self):
        err = APIErrorResponse(
            message="Not found",
            errors=[FieldError(field="id", detail="Resource not found")],
        )
        data = json.loads(err.model_dump_json())
        assert data == {
            "success": False,
            "data": None,
            "message": "Not found",
            "errors": [{"field": "id", "detail": "Resource not found"}],
        }

    def test_multiple_errors(self):
        err = APIErrorResponse(
            message="Validation failed",
            errors=[
                FieldError(field="email", detail="Invalid format"),
                FieldError(field="password", detail="Too short"),
            ],
        )
        assert len(err.errors) == 2


class TestPaginatedMeta:
    def test_creation(self):
        meta = PaginatedMeta(total_count=100, page=2, page_size=20, total_pages=5)
        assert meta.total_count == 100
        assert meta.page == 2
        assert meta.page_size == 20
        assert meta.total_pages == 5

    def test_rejects_negative_total_count(self):
        with pytest.raises(ValidationError):
            PaginatedMeta(total_count=-1, page=1, page_size=20, total_pages=0)

    def test_rejects_zero_page(self):
        with pytest.raises(ValidationError):
            PaginatedMeta(total_count=0, page=0, page_size=20, total_pages=0)

    def test_rejects_page_size_over_100(self):
        with pytest.raises(ValidationError):
            PaginatedMeta(total_count=0, page=1, page_size=101, total_pages=0)


class TestPaginatedResponse:
    def test_paginated_response(self):
        meta = PaginatedMeta(total_count=50, page=1, page_size=20, total_pages=3)
        resp = PaginatedResponse[dict](data=[{"id": "1"}, {"id": "2"}], meta=meta)
        assert resp.success is True
        assert len(resp.data) == 2
        assert resp.meta.total_count == 50

    def test_paginated_response_defaults(self):
        meta = PaginatedMeta(total_count=0, page=1, page_size=20, total_pages=0)
        resp = PaginatedResponse[dict](meta=meta)
        assert resp.success is True
        assert resp.data == []
        assert resp.message == "Success"

    def test_json_format(self):
        meta = PaginatedMeta(total_count=1, page=1, page_size=20, total_pages=1)
        resp = PaginatedResponse[dict](data=[{"name": "Item"}], meta=meta)
        data = json.loads(resp.model_dump_json())
        assert data["success"] is True
        assert data["data"] == [{"name": "Item"}]
        assert data["message"] == "Success"
        assert data["meta"] == {
            "total_count": 1,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
        }

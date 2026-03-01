"""
Tests for Payflex Pydantic schemas: validation, decimal handling, extra fields.
"""
import pytest
from decimal import Decimal
from app.payments.payflex.schemas import (
    PayflexLineItem,
    PayflexAmount,
    PayflexConfigResponse,
    PayflexCreateOrderResponse,
    PayflexOrderStatusResponse,
    PayflexWebhookPayload,
    PayflexRefundRequest,
)


class TestPayflexLineItem:
    def test_valid_item(self):
        item = PayflexLineItem(name="Pokemon Card", quantity=2, price=Decimal("49.99"))
        assert item.price == Decimal("49.99")
        assert item.quantity == 2

    def test_price_coerced_from_float(self):
        item = PayflexLineItem(name="Card", quantity=1, price=49.99)
        assert isinstance(item.price, Decimal)

    def test_invalid_quantity(self):
        with pytest.raises(Exception):
            PayflexLineItem(name="Card", quantity=0, price=Decimal("10"))


class TestPayflexAmount:
    def test_valid_amount(self):
        amt = PayflexAmount(amount=Decimal("500.00"), shipping=Decimal("99.00"))
        assert amt.amount == Decimal("500.00")
        assert amt.currency == "ZAR"

    def test_amount_coerced_from_float(self):
        amt = PayflexAmount(amount=500.00)
        assert isinstance(amt.amount, Decimal)


class TestPayflexConfigResponse:
    def test_parses_config(self):
        config = PayflexConfigResponse.model_validate({
            "minimumAmount": 50,
            "maximumAmount": 10000,
            "someExtraField": "ignored",
        })
        assert config.minimumAmount == Decimal("50")
        assert config.maximumAmount == Decimal("10000")

    def test_extra_fields_ignored(self):
        config = PayflexConfigResponse.model_validate({
            "minimumAmount": 50,
            "maximumAmount": 10000,
            "unknownField": True,
            "anotherUnknown": {"nested": "data"},
        })
        assert not hasattr(config, "unknownField")


class TestPayflexOrderStatusResponse:
    def test_parses_status(self):
        resp = PayflexOrderStatusResponse.model_validate({
            "orderId": "abc-123",
            "orderStatus": "Approved",
            "amount": 500.00,
        })
        assert resp.orderId == "abc-123"
        assert resp.orderStatus == "Approved"
        assert resp.amount == Decimal("500.00")

    def test_null_amount(self):
        resp = PayflexOrderStatusResponse.model_validate({
            "orderId": "abc",
            "orderStatus": "Pending",
        })
        assert resp.amount is None


class TestPayflexWebhookPayload:
    def test_parses_webhook(self):
        payload = PayflexWebhookPayload.model_validate({
            "orderId": "pf-123",
            "orderStatus": "Approved",
            "token": "tok-456",
            "amount": 299.99,
            "extraField": "ignored",
        })
        assert payload.orderId == "pf-123"
        assert payload.amount == Decimal("299.99")


class TestPayflexRefundRequest:
    def test_valid_refund(self):
        req = PayflexRefundRequest(amount=Decimal("100.00"))
        assert req.amount == Decimal("100.00")

    def test_zero_refund_raises(self):
        with pytest.raises(Exception):
            PayflexRefundRequest(amount=Decimal("0"))

    def test_negative_refund_raises(self):
        with pytest.raises(Exception):
            PayflexRefundRequest(amount=Decimal("-10"))


class TestPayflexCreateOrderResponse:
    def test_parses_response(self):
        resp = PayflexCreateOrderResponse.model_validate({
            "token": "tok-abc",
            "expiryDateTime": "2025-12-31T23:59:59Z",
            "redirectUrl": "https://checkout.payflex.co.za/checkout?token=tok-abc",
            "orderId": "pf-order-789",
        })
        assert resp.token == "tok-abc"
        assert resp.orderId == "pf-order-789"
        assert "checkout" in resp.redirectUrl

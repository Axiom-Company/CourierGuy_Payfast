"""
Tests for Payflex webhook handler: successful payment, duplicate delivery,
amount mismatch, and idempotency.
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from app.payments.payflex.webhook import PayflexWebhookHandler
from app.payments.payflex.schemas import PayflexWebhookPayload, PayflexOrderStatusResponse
from app.domain.enums import PaymentStatus, OrderStatus


def _make_order(
    order_number="PKM-00001",
    payment_status=PaymentStatus.PENDING,
    order_status=OrderStatus.PENDING_PAYMENT,
    total_zar=500.00,
    payflex_order_id="pf-123",
):
    order = MagicMock()
    order.id = "order-uuid-1"
    order.order_number = order_number
    order.payment_status = payment_status
    order.order_status = order_status
    order.total_zar = total_zar
    order.payflex_order_id = payflex_order_id
    order.items = []
    return order


@pytest.fixture
def mock_client():
    return AsyncMock()


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def handler(mock_client, mock_repo):
    return PayflexWebhookHandler(mock_client, mock_repo)


# ---------------------------------------------------------------------------
# Successful Payment
# ---------------------------------------------------------------------------

class TestSuccessfulPayment:
    @pytest.mark.asyncio
    async def test_approved_payment_updates_order(self, handler, mock_client, mock_repo):
        order = _make_order()
        mock_repo.get_by_payflex_order_id.return_value = order

        mock_client.get_order.return_value = PayflexOrderStatusResponse(
            orderId="pf-123", orderStatus="Approved", amount=Decimal("500.00")
        )

        payload = PayflexWebhookPayload(orderId="pf-123", orderStatus="Approved", amount=Decimal("500.00"))
        result = await handler.handle(payload)

        assert result["processed"] is True
        assert result["payment_status"] == "complete"
        mock_repo.update_by_id.assert_called_once()
        call_args = mock_repo.update_by_id.call_args[0]
        assert call_args[1]["payment_status"] == PaymentStatus.COMPLETE
        assert call_args[1]["order_status"] == OrderStatus.PAID


# ---------------------------------------------------------------------------
# Duplicate Delivery (Idempotency)
# ---------------------------------------------------------------------------

class TestIdempotency:
    @pytest.mark.asyncio
    async def test_duplicate_webhook_is_noop(self, handler, mock_client, mock_repo):
        order = _make_order(payment_status=PaymentStatus.COMPLETE)
        mock_repo.get_by_payflex_order_id.return_value = order

        payload = PayflexWebhookPayload(orderId="pf-123", orderStatus="Approved")
        result = await handler.handle(payload)

        assert result["processed"] is True
        assert result["reason"] == "already_processed"
        mock_repo.update_by_id.assert_not_called()


# ---------------------------------------------------------------------------
# Order Not Found
# ---------------------------------------------------------------------------

class TestOrderNotFound:
    @pytest.mark.asyncio
    async def test_unknown_order_returns_not_found(self, handler, mock_repo):
        mock_repo.get_by_payflex_order_id.return_value = None

        payload = PayflexWebhookPayload(orderId="pf-unknown", orderStatus="Approved")
        result = await handler.handle(payload)

        assert result["processed"] is False
        assert result["reason"] == "order_not_found"


# ---------------------------------------------------------------------------
# Amount Mismatch
# ---------------------------------------------------------------------------

class TestAmountMismatch:
    @pytest.mark.asyncio
    async def test_amount_mismatch_flags_for_review(self, handler, mock_client, mock_repo):
        order = _make_order(total_zar=500.00)
        mock_repo.get_by_payflex_order_id.return_value = order

        # Payflex reports different amount
        mock_client.get_order.return_value = PayflexOrderStatusResponse(
            orderId="pf-123", orderStatus="Approved", amount=Decimal("999.99")
        )

        payload = PayflexWebhookPayload(orderId="pf-123", orderStatus="Approved", amount=Decimal("999.99"))
        result = await handler.handle(payload)

        assert result["processed"] is False
        assert result["reason"] == "amount_mismatch"
        # Should have been called to add seller_notes
        assert mock_repo.update_by_id.call_count == 1
        notes = mock_repo.update_by_id.call_args[0][1]["seller_notes"]
        assert "AMOUNT MISMATCH" in notes


# ---------------------------------------------------------------------------
# Declined / Cancelled
# ---------------------------------------------------------------------------

class TestDeclinedCancelled:
    @pytest.mark.asyncio
    async def test_declined_updates_status(self, handler, mock_client, mock_repo):
        order = _make_order()
        mock_repo.get_by_payflex_order_id.return_value = order

        mock_client.get_order.return_value = PayflexOrderStatusResponse(
            orderId="pf-123", orderStatus="Declined", amount=Decimal("500.00")
        )

        payload = PayflexWebhookPayload(orderId="pf-123", orderStatus="Declined")
        result = await handler.handle(payload)

        assert result["processed"] is True
        call_args = mock_repo.update_by_id.call_args[0]
        assert call_args[1]["payment_status"] == PaymentStatus.FAILED
        assert call_args[1]["order_status"] == OrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancelled_updates_status(self, handler, mock_client, mock_repo):
        order = _make_order()
        mock_repo.get_by_payflex_order_id.return_value = order

        mock_client.get_order.return_value = PayflexOrderStatusResponse(
            orderId="pf-123", orderStatus="Cancelled", amount=Decimal("500.00")
        )

        payload = PayflexWebhookPayload(orderId="pf-123", orderStatus="Cancelled")
        result = await handler.handle(payload)

        assert result["processed"] is True
        call_args = mock_repo.update_by_id.call_args[0]
        assert call_args[1]["payment_status"] == PaymentStatus.CANCELLED


# ---------------------------------------------------------------------------
# Verification Failure
# ---------------------------------------------------------------------------

class TestVerificationFailure:
    @pytest.mark.asyncio
    async def test_api_verification_failure_returns_gracefully(self, handler, mock_client, mock_repo):
        order = _make_order()
        mock_repo.get_by_payflex_order_id.return_value = order

        mock_client.get_order.side_effect = Exception("Payflex API down")

        payload = PayflexWebhookPayload(orderId="pf-123", orderStatus="Approved")
        result = await handler.handle(payload)

        assert result["processed"] is False
        assert result["reason"] == "verification_failed"
        mock_repo.update_by_id.assert_not_called()

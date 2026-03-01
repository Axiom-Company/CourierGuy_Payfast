"""
Tests for PayflexClient: OAuth token caching, create order, get order,
refund, circuit breaker, retry logic, and error handling.
"""
import pytest
import time
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

import httpx

from app.payments.payflex.client import PayflexClient, CircuitBreaker, PayflexServiceUnavailable, _TokenCache
from app.payments.payflex.config import PayflexSettings


@pytest.fixture
def settings():
    return PayflexSettings(
        payflex_mode="sandbox",
        payflex_client_id="test_client_id",
        payflex_client_secret="test_client_secret",
        payflex_redirect_url="http://localhost:3000/checkout/payflex/return",
        payflex_callback_url="http://localhost:8000/api/payments/payflex/webhook",
    )


@pytest.fixture
def client(settings):
    return PayflexClient(settings)


# ---------------------------------------------------------------------------
# Token Cache
# ---------------------------------------------------------------------------

class TestTokenCache:
    def test_initially_invalid(self):
        cache = _TokenCache()
        assert not cache.is_valid()

    def test_valid_after_store(self):
        cache = _TokenCache()
        cache.store("test_token", 3600)
        assert cache.is_valid()
        assert cache.token == "test_token"

    def test_invalid_after_clear(self):
        cache = _TokenCache()
        cache.store("test_token", 3600)
        cache.clear()
        assert not cache.is_valid()

    def test_invalid_when_near_expiry(self):
        cache = _TokenCache()
        cache.store("test_token", 30)  # Only 30s until expiry, less than 60s buffer
        assert not cache.is_valid()


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class TestCircuitBreaker:
    def test_initially_closed(self):
        cb = CircuitBreaker(threshold=3, recovery_seconds=300)
        assert not cb.is_open

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(threshold=3, recovery_seconds=300)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open
        cb.record_failure()
        assert cb.is_open

    def test_resets_on_success(self):
        cb = CircuitBreaker(threshold=2, recovery_seconds=300)
        cb.record_failure()
        cb.record_success()
        cb.record_failure()
        assert not cb.is_open

    def test_half_open_after_recovery(self):
        cb = CircuitBreaker(threshold=1, recovery_seconds=0)
        cb.record_failure()
        # With recovery_seconds=0, should immediately allow
        assert not cb.is_open


# ---------------------------------------------------------------------------
# OAuth Token Management
# ---------------------------------------------------------------------------

class TestOAuthToken:
    @pytest.mark.asyncio
    async def test_get_token_caches(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "cached_token", "expires_in": 3600}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, '_ensure_http') as mock_http:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_http.return_value = mock_client

            token1 = await client._get_token()
            token2 = await client._get_token()

            assert token1 == "cached_token"
            assert token2 == "cached_token"
            # Should only call auth endpoint once (cached on second call)
            assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_get_token_refreshes_when_expired(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "new_token", "expires_in": 3600}
        mock_response.raise_for_status = MagicMock()

        # Pre-expire the cache
        client._token_cache.store("old_token", 0)

        with patch.object(client, '_ensure_http') as mock_http:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_http.return_value = mock_client

            token = await client._get_token()
            assert token == "new_token"


# ---------------------------------------------------------------------------
# Create Order
# ---------------------------------------------------------------------------

class TestCreateOrder:
    @pytest.mark.asyncio
    async def test_create_order_happy_path(self, client):
        # Mock config response
        config_resp = MagicMock()
        config_resp.status_code = 200
        config_resp.json.return_value = {"minimumAmount": 50, "maximumAmount": 10000}
        config_resp.raise_for_status = MagicMock()

        # Mock create order response
        order_resp = MagicMock()
        order_resp.status_code = 200
        order_resp.json.return_value = {
            "token": "test-token-123",
            "expiryDateTime": "2025-12-31T23:59:59Z",
            "redirectUrl": "https://checkout.sandbox.payflex.co.za/checkout?token=test-token-123",
            "orderId": "pf-order-456",
        }
        order_resp.raise_for_status = MagicMock()

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = [config_resp, order_resp]

            payload = {
                "amount": {"amount": 500, "currency": "ZAR"},
                "consumer": {"email": "test@test.com", "givenNames": "Test", "surname": "User"},
            }
            result = await client.create_order(payload)
            assert result.orderId == "pf-order-456"
            assert result.token == "test-token-123"

    @pytest.mark.asyncio
    async def test_create_order_amount_out_of_range(self, client):
        config_resp = MagicMock()
        config_resp.status_code = 200
        config_resp.json.return_value = {"minimumAmount": 100, "maximumAmount": 5000}
        config_resp.raise_for_status = MagicMock()

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = config_resp

            payload = {"amount": {"amount": 50, "currency": "ZAR"}}
            with pytest.raises(ValueError, match="outside Payflex's allowed range"):
                await client.create_order(payload)


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------

class TestRefund:
    @pytest.mark.asyncio
    async def test_refund_full(self, client):
        refund_resp = MagicMock()
        refund_resp.status_code = 200
        refund_resp.json.return_value = {
            "refundId": "ref-123",
            "orderId": "ord-456",
            "amount": 500,
            "status": "completed",
        }
        refund_resp.raise_for_status = MagicMock()

        with patch.object(client, '_request', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = refund_resp
            result = await client.refund("ord-456", Decimal("500.00"))
            assert result.refundId == "ref-123"

    @pytest.mark.asyncio
    async def test_refund_zero_amount_raises(self, client):
        with pytest.raises(ValueError, match="positive"):
            await client.refund("ord-456", Decimal("0"))

    @pytest.mark.asyncio
    async def test_refund_negative_amount_raises(self, client):
        with pytest.raises(ValueError, match="positive"):
            await client.refund("ord-456", Decimal("-10"))


# ---------------------------------------------------------------------------
# Circuit Breaker Integration
# ---------------------------------------------------------------------------

class TestCircuitBreakerIntegration:
    @pytest.mark.asyncio
    async def test_request_fails_when_circuit_open(self, client):
        client.circuit_breaker._failure_count = 3
        client.circuit_breaker._opened_at = time.monotonic()

        with pytest.raises(PayflexServiceUnavailable, match="circuit breaker"):
            await client._request("GET", "/test")


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_passes(self, client):
        with patch.object(client, 'get_configuration', new_callable=AsyncMock) as mock_config:
            from app.payments.payflex.schemas import PayflexConfigResponse
            mock_config.return_value = PayflexConfigResponse(minimumAmount=Decimal("50"), maximumAmount=Decimal("10000"))
            result = await client.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_fails(self, client):
        with patch.object(client, 'get_configuration', new_callable=AsyncMock) as mock_config:
            mock_config.side_effect = Exception("Connection refused")
            result = await client.health_check()
            assert result is False

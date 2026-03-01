"""
Payflex API client.

Handles OAuth2 token management with auto-refresh, HTTP retries for 5xx/timeouts,
structured logging, and a circuit breaker to disable Payflex when their API is down.

All money amounts are Decimal. Never float.
"""
from __future__ import annotations

import logging
import time
from decimal import Decimal
from typing import Any

import httpx

from app.payments.payflex.config import PayflexSettings, get_payflex_settings
from app.payments.payflex.schemas import (
    PayflexConfigResponse,
    PayflexCreateOrderResponse,
    PayflexOrderStatusResponse,
    PayflexRefundResponse,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """
    Simple circuit breaker: after `threshold` consecutive failures, open the
    circuit for `recovery_seconds`. During that window all calls fail fast.
    """

    def __init__(self, threshold: int = 3, recovery_seconds: int = 300):
        self.threshold = threshold
        self.recovery_seconds = recovery_seconds
        self._failure_count = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        elapsed = time.monotonic() - self._opened_at
        if elapsed >= self.recovery_seconds:
            # Half-open: allow one attempt
            return False
        return True

    def record_success(self) -> None:
        self._failure_count = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self.threshold:
            self._opened_at = time.monotonic()
            logger.error(
                "Payflex circuit breaker OPEN — %d consecutive failures. "
                "Will retry in %d seconds.",
                self._failure_count,
                self.recovery_seconds,
            )


# ---------------------------------------------------------------------------
# OAuth Token Cache
# ---------------------------------------------------------------------------

class _TokenCache:
    """In-memory cache for the Payflex OAuth bearer token."""

    def __init__(self):
        self.token: str | None = None
        self.expires_at: float = 0.0  # monotonic timestamp

    def is_valid(self) -> bool:
        """True if token exists and won't expire within the next 60 seconds."""
        return self.token is not None and time.monotonic() < (self.expires_at - 60)

    def store(self, token: str, expires_in: int) -> None:
        self.token = token
        self.expires_at = time.monotonic() + expires_in

    def clear(self) -> None:
        self.token = None
        self.expires_at = 0.0


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class PayflexClient:
    """
    Async HTTP client for the Payflex API.

    Usage:
        client = PayflexClient()
        async with client:
            config = await client.get_configuration()
            resp = await client.create_order(payload)
    """

    _MAX_RETRIES = 3
    _BACKOFF_BASE = 1  # seconds

    def __init__(self, settings: PayflexSettings | None = None):
        self._settings = settings or get_payflex_settings()
        self._token_cache = _TokenCache()
        self._http: httpx.AsyncClient | None = None
        self._config_cache: PayflexConfigResponse | None = None
        self._config_fetched_at: float = 0.0
        self.circuit_breaker = CircuitBreaker(threshold=3, recovery_seconds=300)

    # -- lifecycle ----------------------------------------------------------

    async def __aenter__(self) -> "PayflexClient":
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
        )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    def _ensure_http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
            )
        return self._http

    # -- auth ---------------------------------------------------------------

    async def _get_token(self) -> str:
        """
        Return a valid bearer token, refreshing if necessary.

        Raises httpx.HTTPStatusError on auth failure.
        """
        if self._token_cache.is_valid():
            return self._token_cache.token  # type: ignore[return-value]

        http = self._ensure_http()
        payload = {
            "client_id": self._settings.payflex_client_id,
            "client_secret": self._settings.payflex_client_secret,
            "audience": self._settings.payflex_audience,
            "grant_type": "client_credentials",
        }

        start = time.monotonic()
        resp = await http.post(
            self._settings.payflex_auth_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info("Payflex auth POST %s → %d (%dms)", self._settings.payflex_auth_url, resp.status_code, duration_ms)

        resp.raise_for_status()
        data = resp.json()

        token = data.get("access_token", "")
        expires_in = int(data.get("expires_in", 3600))
        self._token_cache.store(token, expires_in)
        return token

    # -- internal request with retry ----------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        params: dict | None = None,
    ) -> httpx.Response:
        """
        Make an authenticated request to the Payflex API with retry logic.

        Retries up to _MAX_RETRIES times for 5xx and timeout errors only.
        Never retries 4xx (client errors).
        """
        if self.circuit_breaker.is_open:
            raise PayflexServiceUnavailable("Payflex circuit breaker is open — service temporarily disabled")

        http = self._ensure_http()
        url = f"{self._settings.payflex_api_url}{path}"

        last_exc: Exception | None = None

        for attempt in range(self._MAX_RETRIES + 1):
            try:
                token = await self._get_token()
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

                start = time.monotonic()
                resp = await http.request(method, url, json=json_body, params=params, headers=headers)
                duration_ms = int((time.monotonic() - start) * 1000)

                # Structured logging (redact sensitive fields)
                log_body = _redact(json_body) if json_body else None
                logger.info(
                    "Payflex %s %s → %d (%dms) body=%s",
                    method, path, resp.status_code, duration_ms, log_body,
                )

                if resp.status_code < 500:
                    # 2xx or 4xx — don't retry
                    self.circuit_breaker.record_success()
                    return resp

                # 5xx — retry
                last_exc = httpx.HTTPStatusError(
                    f"Server error {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )

            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                logger.warning("Payflex %s %s attempt %d failed: %s", method, path, attempt + 1, exc)

            # Exponential backoff before retry
            if attempt < self._MAX_RETRIES:
                import asyncio
                wait = self._BACKOFF_BASE * (2 ** attempt)
                await asyncio.sleep(wait)

        # All retries exhausted
        self.circuit_breaker.record_failure()
        raise PayflexServiceUnavailable(f"Payflex API unavailable after {self._MAX_RETRIES + 1} attempts: {last_exc}")

    # -- public API methods -------------------------------------------------

    async def get_configuration(self, *, force: bool = False) -> PayflexConfigResponse:
        """
        GET /configuration — returns min/max payment amounts.

        Cached for 1 hour unless force=True.
        """
        now = time.monotonic()
        if not force and self._config_cache and (now - self._config_fetched_at) < 3600:
            return self._config_cache

        resp = await self._request("GET", "/configuration")
        resp.raise_for_status()
        data = resp.json()

        self._config_cache = PayflexConfigResponse.model_validate(data)
        self._config_fetched_at = now
        return self._config_cache

    async def create_order(self, payload: dict) -> PayflexCreateOrderResponse:
        """
        POST /order — create a Payflex order and get a checkout redirect URL.

        Validates the total amount is within Payflex's configured range BEFORE
        calling the API. Raises ValueError if out of range.
        """
        # Pre-validate amount range
        config = await self.get_configuration()
        total = Decimal(str(payload.get("amount", {}).get("amount", 0)))
        if total < config.minimumAmount or total > config.maximumAmount:
            raise ValueError(
                f"Order total R{total} is outside Payflex's allowed range "
                f"(R{config.minimumAmount}–R{config.maximumAmount})"
            )

        resp = await self._request("POST", "/order", json_body=payload)
        resp.raise_for_status()
        return PayflexCreateOrderResponse.model_validate(resp.json())

    async def get_order(self, order_id: str) -> PayflexOrderStatusResponse:
        """
        GET /order/{orderId} — retrieve current order status from Payflex.

        Used for:
        - Verifying webhook payloads (never trust the webhook alone)
        - Polling pending orders
        - Return-page status checks
        """
        resp = await self._request("GET", f"/order/{order_id}")
        resp.raise_for_status()
        return PayflexOrderStatusResponse.model_validate(resp.json())

    async def refund(self, order_id: str, amount: Decimal) -> PayflexRefundResponse:
        """
        POST /order/{orderId}/refund — process a full or partial refund.

        Amount must be positive and in ZAR.
        """
        if amount <= 0:
            raise ValueError("Refund amount must be positive")

        resp = await self._request(
            "POST",
            f"/order/{order_id}/refund",
            json_body={"amount": str(amount)},
        )
        resp.raise_for_status()
        return PayflexRefundResponse.model_validate(resp.json())

    async def health_check(self) -> bool:
        """Quick connectivity check — calls GET /configuration."""
        try:
            await self.get_configuration(force=True)
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PayflexServiceUnavailable(Exception):
    """Raised when Payflex API is unreachable or circuit breaker is open."""
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _redact(data: dict | None) -> dict | None:
    """Redact sensitive fields for logging."""
    if data is None:
        return None
    redacted = dict(data)
    for key in ("client_secret", "client_id", "phoneNumber", "phone_number"):
        if key in redacted:
            redacted[key] = "***"
    # Redact nested consumer fields
    if "consumer" in redacted and isinstance(redacted["consumer"], dict):
        consumer = dict(redacted["consumer"])
        for k in ("email", "phoneNumber", "phone_number"):
            if k in consumer:
                consumer[k] = "***"
        redacted["consumer"] = consumer
    return redacted

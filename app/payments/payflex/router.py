"""
Payflex FastAPI routes.

POST /api/v1/payments/payflex/create-order    → Initiate Payflex checkout
GET  /api/v1/payments/payflex/order/{id}      → Get order status
POST /api/v1/payments/payflex/refund/{id}     → Process refund
GET  /api/v1/payments/payflex/return          → Handle customer redirect back
POST /api/v1/payments/payflex/webhook         → Receive Payflex status callbacks
GET  /api/v1/payments/payflex/configuration   → Get min/max amounts
"""
from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse

from app.payments.payflex.client import PayflexClient, PayflexServiceUnavailable
from app.payments.payflex.config import get_payflex_settings
from app.payments.payflex.schemas import (
    PayflexCreateOrderRequest,
    PayflexWebhookPayload,
    PayflexRefundRequest,
    PayflexCheckoutResponse,
    PayflexOrderStatusPublic,
    PayflexConfigPublic,
)
from app.payments.payflex.webhook import PayflexWebhookHandler
from app.payments.schemas import make_payflex_error
from app.repositories.order_repo import OrderRepository
from app.repositories.product_repo import ProductRepository
from app.domain.enums import PaymentStatus, OrderStatus
from app.api.deps import get_order_service, require_admin_api_key

from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments/payflex", tags=["Payflex"])


# ---------------------------------------------------------------------------
# Singleton client — avoids leaking httpx.AsyncClient on every request
# ---------------------------------------------------------------------------

_payflex_client: PayflexClient | None = None


def _get_payflex_client() -> PayflexClient:
    """Return a module-level singleton PayflexClient.
    The client's _ensure_http() lazily creates and reuses one AsyncClient."""
    global _payflex_client
    settings = get_payflex_settings()
    if not settings.is_configured:
        raise HTTPException(503, "Payflex is not configured")
    if _payflex_client is None:
        _payflex_client = PayflexClient(settings)
    return _payflex_client


def _get_order_repo(db: AsyncSession = Depends(get_db)) -> OrderRepository:
    return OrderRepository(db)


def _get_product_repo(db: AsyncSession = Depends(get_db)) -> ProductRepository:
    return ProductRepository(db)


# ---------------------------------------------------------------------------
# GET /configuration
# ---------------------------------------------------------------------------

@router.get("/configuration")
async def get_configuration():
    """Return Payflex min/max amounts and availability status."""
    settings = get_payflex_settings()
    if not settings.is_configured:
        return PayflexConfigPublic(available=False)

    client = _get_payflex_client()
    try:
        config = await client.get_configuration()
        return PayflexConfigPublic(
            available=not client.circuit_breaker.is_open,
            min_amount=str(config.minimumAmount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            max_amount=str(config.maximumAmount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        )
    except Exception as exc:
        logger.warning("Failed to fetch Payflex configuration: %s", exc)
        return PayflexConfigPublic(available=False)


# ---------------------------------------------------------------------------
# POST /create-order
# ---------------------------------------------------------------------------

@router.post("/create-order")
async def create_order(
    data: PayflexCreateOrderRequest,
    order_repo: OrderRepository = Depends(_get_order_repo),
):
    """
    Initiate a Payflex checkout for an existing order.

    The order must already exist in our database (created during the standard
    checkout flow). This endpoint:
    1. Validates the order exists and hasn't been paid.
    2. Checks a Payflex order hasn't already been created for it.
    3. Recalculates the total server-side (NEVER trust frontend amounts).
    4. Creates the Payflex order and returns the redirect URL.
    """
    settings = get_payflex_settings()
    if not settings.is_configured:
        return JSONResponse(
            status_code=503,
            content=make_payflex_error("PAYFLEX_SERVICE_UNAVAILABLE").model_dump(),
        )

    # Find order
    order = await order_repo.get_by_order_number(data.order_id)
    if not order:
        order = await order_repo.get_by_id(data.order_id)
    if not order:
        return JSONResponse(
            status_code=404,
            content=make_payflex_error("PAYFLEX_ORDER_NOT_FOUND", order_id=data.order_id).model_dump(),
        )

    # Already paid?
    if order.payment_status == PaymentStatus.COMPLETE:
        return JSONResponse(
            status_code=400,
            content=make_payflex_error("PAYFLEX_ALREADY_PAID", order_id=order.order_number).model_dump(),
        )

    # Already has a Payflex order? (debounce double-clicks)
    if order.payflex_order_id:
        # Check if it's still valid by querying Payflex
        client = _get_payflex_client()
        try:
            existing = await client.get_order(order.payflex_order_id)
            if existing.orderStatus in ("Pending", ""):
                # Reuse existing checkout URL
                checkout_url = f"{settings.payflex_checkout_url}/checkout?token={order.payflex_token}"
                return PayflexCheckoutResponse(
                    redirect_url=checkout_url,
                    payflex_order_id=order.payflex_order_id,
                    token=order.payflex_token or "",
                )
        except Exception:
            pass  # Stale order — create a new one

    # Build Payflex payload from our order data (server-side totals, never frontend)
    total = Decimal(str(order.total_zar))
    shipping = Decimal(str(order.shipping_cost_zar))
    email = order.guest_email or ""
    name = order.guest_name or ""
    parts = name.split(" ", 1)
    phone = order.guest_phone or ""

    # Line items from order items
    items = []
    for item in order.items:
        items.append({
            "name": item.product_name[:100],
            "quantity": item.quantity,
            "price": float(Decimal(str(item.unit_price_zar)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        })

    payload = {
        "consumer": {
            "email": email,
            "givenNames": parts[0] if parts else "",
            "surname": parts[1] if len(parts) > 1 else parts[0] if parts else "",
            "phoneNumber": phone,
        },
        "orderDetails": {
            "items": items,
        },
        "shipping": {
            "name": name,
            "line1": order.shipping_address_line1 or "",
            "city": order.shipping_city or "",
            "postcode": order.shipping_postal_code or "",
            "region": order.shipping_province or "",
            "country": "ZA",
        },
        "billing": {
            "name": name,
            "line1": order.shipping_address_line1 or "",
            "city": order.shipping_city or "",
            "postcode": order.shipping_postal_code or "",
            "region": order.shipping_province or "",
            "country": "ZA",
        },
        "amount": {
            "amount": float(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "currency": "ZAR",
            "shipping": float(shipping.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        },
        "merchant": {
            "redirectUrl": f"{settings.payflex_redirect_url}?order={order.order_number}",
            "statusCallbackUrl": settings.payflex_callback_url,
        },
        "redirectUrl": f"{settings.payflex_redirect_url}?order={order.order_number}",
        "statusCallbackUrl": settings.payflex_callback_url,
    }

    client = _get_payflex_client()
    try:
        result = await client.create_order(payload)
    except ValueError as exc:
        # Amount out of range
        return JSONResponse(
            status_code=400,
            content=make_payflex_error(
                "PAYFLEX_AMOUNT_OUT_OF_RANGE",
                detail=str(exc),
                order_id=order.order_number,
            ).model_dump(),
        )
    except PayflexServiceUnavailable as exc:
        return JSONResponse(
            status_code=503,
            content=make_payflex_error(
                "PAYFLEX_SERVICE_UNAVAILABLE",
                detail=str(exc),
                order_id=order.order_number,
            ).model_dump(),
        )
    except Exception as exc:
        logger.error("Payflex create order failed: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content=make_payflex_error(
                "PAYFLEX_ORDER_CREATE_FAILED",
                detail=str(exc),
                order_id=order.order_number,
                retry_allowed=True,
            ).model_dump(),
        )

    # Persist Payflex order details on our order
    await order_repo.update_by_id(order.id, {
        "payment_provider": "payflex",
        "payflex_order_id": result.orderId,
        "payflex_token": result.token,
    })

    return PayflexCheckoutResponse(
        redirect_url=result.redirectUrl,
        payflex_order_id=result.orderId,
        token=result.token,
        expires_at=result.expiryDateTime,
    )


# ---------------------------------------------------------------------------
# GET /order/{order_number}
# ---------------------------------------------------------------------------

@router.get("/order/{order_number}")
async def get_order_status(
    order_number: str,
    order_repo: OrderRepository = Depends(_get_order_repo),
):
    """Get the current status of a Payflex order (used by the return page)."""
    order = await order_repo.get_by_order_number(order_number)
    if not order:
        raise HTTPException(404, "Order not found")

    return PayflexOrderStatusPublic(
        order_id=order.id,
        order_number=order.order_number,
        payflex_order_id=order.payflex_order_id,
        status=order.order_status.value if hasattr(order.order_status, "value") else str(order.order_status),
        payment_status=order.payment_status.value if hasattr(order.payment_status, "value") else str(order.payment_status),
        total_zar=f"{Decimal(str(order.total_zar)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}",
        provider=order.payment_provider or "payfast",
    )


# ---------------------------------------------------------------------------
# POST /webhook
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def payflex_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    order_repo: OrderRepository = Depends(_get_order_repo),
):
    """
    Receive Payflex status callback.

    Returns 200 immediately. Heavy processing (stock reduction, shipping booking)
    happens in the background via the webhook handler.
    """
    try:
        body = await request.json()
    except Exception:
        logger.error("Payflex webhook: invalid JSON body")
        return JSONResponse(status_code=200, content={"received": True})

    # Redact PII before logging
    from app.payments.payflex.client import _redact
    logger.info("Payflex webhook payload: %s", _redact(body) if isinstance(body, dict) else "(non-dict)")

    try:
        payload = PayflexWebhookPayload.model_validate(body)
    except Exception as exc:
        logger.error("Payflex webhook: payload validation failed: %s", exc)
        return JSONResponse(status_code=200, content={"received": True, "error": "invalid_payload"})

    client = _get_payflex_client()
    handler = PayflexWebhookHandler(client, order_repo)

    # Process in the current request (webhook handler is designed to be fast)
    # but reduce stock in the background
    result = await handler.handle(payload)

    if result.get("processed") and result.get("payment_status") == "complete":
        order = await order_repo.get_by_payflex_order_id(payload.orderId)
        if order:
            background_tasks.add_task(_reduce_stock_bg, order, order_repo)

    return JSONResponse(status_code=200, content={"received": True, **result})


async def _reduce_stock_bg(order, order_repo: OrderRepository):
    """Background task: reduce stock after successful Payflex payment."""
    try:
        from app.repositories.product_repo import ProductRepository
        # We need a fresh session for background tasks
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            product_repo = ProductRepository(session)
            for item in order.items:
                await product_repo.reduce_stock(item.product_id, item.quantity)
            await session.commit()
    except Exception as exc:
        logger.error("Failed to reduce stock for order %s: %s", order.order_number, exc)


# ---------------------------------------------------------------------------
# GET /return
# ---------------------------------------------------------------------------

@router.get("/return")
async def payflex_return(
    request: Request,
    order_repo: OrderRepository = Depends(_get_order_repo),
):
    """
    Handle customer redirect back from Payflex.

    URL params may include token, orderId, status — but we NEVER trust them.
    Always verify from our database (which may have been updated by the webhook already).
    """
    params = dict(request.query_params)
    order_number = params.get("order", "")
    token = params.get("token", "")

    if not order_number and not token:
        raise HTTPException(400, "Missing order reference")

    # Look up by order number first, then by token
    order = None
    if order_number:
        order = await order_repo.get_by_order_number(order_number)
    if not order and token:
        order = await order_repo.get_by_payflex_token(token)

    if not order:
        raise HTTPException(404, "Order not found")

    # If order is still pending and has a payflex_order_id, poll Payflex for latest status
    if order.payment_status == PaymentStatus.PENDING and order.payflex_order_id:
        settings = get_payflex_settings()
        client = _get_payflex_client()
        try:
            pf_status = await client.get_order(order.payflex_order_id)
            # Update if Payflex has a definitive status
            if pf_status.orderStatus == "Approved" and order.payment_status != PaymentStatus.COMPLETE:
                await order_repo.update_by_id(order.id, {
                    "payment_status": PaymentStatus.COMPLETE,
                    "order_status": OrderStatus.PAID,
                    "payflex_payment_id": order.payflex_order_id,
                })
                order.payment_status = PaymentStatus.COMPLETE
                order.order_status = OrderStatus.PAID
            elif pf_status.orderStatus in ("Declined", "Cancelled"):
                new_ps = PaymentStatus.FAILED if pf_status.orderStatus == "Declined" else PaymentStatus.CANCELLED
                await order_repo.update_by_id(order.id, {
                    "payment_status": new_ps,
                    "order_status": OrderStatus.CANCELLED,
                })
                order.payment_status = new_ps
                order.order_status = OrderStatus.CANCELLED
        except Exception as exc:
            logger.warning("Failed to poll Payflex status on return: %s", exc)

    return PayflexOrderStatusPublic(
        order_id=order.id,
        order_number=order.order_number,
        payflex_order_id=order.payflex_order_id,
        status=order.order_status.value if hasattr(order.order_status, "value") else str(order.order_status),
        payment_status=order.payment_status.value if hasattr(order.payment_status, "value") else str(order.payment_status),
        total_zar=f"{Decimal(str(order.total_zar)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}",
        provider="payflex",
    )


# ---------------------------------------------------------------------------
# POST /refund/{order_number}
# ---------------------------------------------------------------------------

@router.post("/refund/{order_number}", dependencies=[Depends(require_admin_api_key)])
async def refund_order(
    order_number: str,
    data: PayflexRefundRequest,
    order_repo: OrderRepository = Depends(_get_order_repo),
):
    """Process a full or partial refund via Payflex. Requires admin API key."""
    order = await order_repo.get_by_order_number(order_number)
    if not order:
        raise HTTPException(404, "Order not found")

    if not order.payflex_order_id:
        raise HTTPException(400, "Order was not paid via Payflex")

    if order.payment_status != PaymentStatus.COMPLETE:
        raise HTTPException(400, "Order has not been paid")

    # Validate refund amount
    total = Decimal(str(order.total_zar))
    if data.amount > total:
        raise HTTPException(400, f"Refund amount R{data.amount} exceeds order total R{total}")

    settings = get_payflex_settings()
    client = _get_payflex_client()
    try:
        result = await client.refund(order.payflex_order_id, data.amount)
    except Exception as exc:
        logger.error("Payflex refund failed for order %s: %s", order_number, exc)
        return JSONResponse(
            status_code=500,
            content=make_payflex_error(
                "PAYFLEX_REFUND_FAILED",
                detail=str(exc),
                order_id=order_number,
            ).model_dump(),
        )

    # Update order status if full refund
    if data.amount >= total:
        await order_repo.update_by_id(order.id, {
            "payment_status": PaymentStatus.CANCELLED,
            "order_status": OrderStatus.REFUNDED,
        })

    return {
        "success": True,
        "refund_amount": str(data.amount),
        "order_number": order_number,
        "result": result.model_dump() if hasattr(result, "model_dump") else {},
    }

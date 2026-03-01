"""Marketplace PayFast payment endpoints — ported from EliteTCG_API/routes/payfast.js."""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.domain.schemas.marketplace import MarketplaceCreatePaymentRequest
from app.api.deps import get_marketplace_payment_service, optional_current_user_id, get_current_user_id
from app.services.marketplace_payment_service import MarketplacePaymentService

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


@router.post("/payfast/create-payment")
async def create_payment(
    data: MarketplaceCreatePaymentRequest,
    user_id: str | None = Depends(optional_current_user_id),
    service: MarketplacePaymentService = Depends(get_marketplace_payment_service),
):
    try:
        result = await service.create_payment(
            listing_id=data.listing_id,
            quantity=data.quantity,
            buyer_email=data.buyer_email,
            buyer_name=data.buyer_name,
            buyer_phone=data.buyer_phone,
            shipping_address=data.shipping_address.model_dump() if data.shipping_address else None,
            buyer_id=user_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/payfast/notify")
async def marketplace_itn(
    request: Request,
    service: MarketplacePaymentService = Depends(get_marketplace_payment_service),
):
    form = await request.form()
    posted = dict(form)
    await service.handle_marketplace_itn(posted)
    return "OK"


@router.get("/payfast/return")
async def payfast_return():
    settings = get_settings()
    return RedirectResponse(settings.payfast_marketplace_return_url)


@router.get("/payfast/cancel")
async def payfast_cancel():
    settings = get_settings()
    return RedirectResponse(settings.payfast_marketplace_cancel_url)


@router.get("/order/{order_id}")
async def get_order(
    order_id: str,
    user_id: str | None = Depends(optional_current_user_id),
    service: MarketplacePaymentService = Depends(get_marketplace_payment_service),
):
    result = await service.get_order_status(order_id, user_id)
    if not result:
        raise HTTPException(404, "Order not found")
    return result


@router.patch("/order/{order_id}/confirm-delivery")
async def confirm_delivery(
    order_id: str,
    user_id: str = Depends(get_current_user_id),
    service: MarketplacePaymentService = Depends(get_marketplace_payment_service),
):
    try:
        return await service.confirm_delivery(order_id, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except PermissionError:
        raise HTTPException(403, "Not authorized")

from fastapi import APIRouter, Depends, HTTPException, Request
from app.domain.schemas.shipping import ShippingQuoteRequest, ShippingQuoteResponse, ShipmentBookRequest, ShipmentBookResponse
from app.services.shipping_service import ShippingService
from app.api.deps import get_shipping_service, require_admin
from app.domain.models.user import Profile

router = APIRouter(prefix="/shipping", tags=["Shipping"])


@router.post("/quote", response_model=ShippingQuoteResponse)
async def quote(data: ShippingQuoteRequest, service: ShippingService = Depends(get_shipping_service)):
    try:
        return await service.get_quote(data.address_line1, data.city, data.province, data.postal_code,
                                        data.total_weight_grams or 500)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/book", response_model=ShipmentBookResponse)
async def book(data: ShipmentBookRequest, admin: Profile = Depends(require_admin),
               service: ShippingService = Depends(get_shipping_service)):
    try:
        return await service.book_shipment(data.order_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/webhook/courier-guy")
async def courier_webhook(request: Request, service: ShippingService = Depends(get_shipping_service)):
    body = await request.body()
    sig = request.headers.get("X-Signature", "")
    if not service.courier_client.verify_webhook(body, sig):
        raise HTTPException(403, "Invalid webhook signature")
    data = await request.json()
    await service.handle_webhook(data.get("tracking_number", ""), data.get("status", ""))
    return {"status": "ok"}

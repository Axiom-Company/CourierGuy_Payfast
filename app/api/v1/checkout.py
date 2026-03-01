from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from app.domain.schemas.checkout import CheckoutRequest
from app.domain.schemas.direct_checkout import DirectCheckoutRequest
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.api.deps import get_order_service, get_payment_service, get_current_user_optional
from app.domain.models.user import User

router = APIRouter(prefix="/checkout", tags=["Checkout"])


@router.post("/create-order")
async def create_order(data: CheckoutRequest, user: User | None = Depends(get_current_user_optional),
                       order_service: OrderService = Depends(get_order_service),
                       payment_service: PaymentService = Depends(get_payment_service)):
    try:
        order = await order_service.create_from_cart(user, data)
        checkout = payment_service.generate_checkout(order)
        return {"order": order, **checkout}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/direct")
async def direct_checkout(data: DirectCheckoutRequest,
                          order_service: OrderService = Depends(get_order_service),
                          payment_service: PaymentService = Depends(get_payment_service)):
    """Direct checkout from external frontend — no auth or cart required.
    Accepts items, customer info, and shipping details directly.
    Supports payment_provider='payfast' (default) or 'payflex'."""
    try:
        order = await order_service.create_direct(data)

        if data.payment_provider == "payflex":
            # For Payflex: create the order in our DB first, then the frontend
            # will call /api/v1/payments/payflex/create-order with the order number.
            # We just return the order data and a flag so the frontend knows
            # to redirect to the Payflex create-order endpoint instead of PayFast.
            return {
                "order": order,
                "payment_provider": "payflex",
                "order_number": order.order_number,
            }

        checkout = payment_service.generate_checkout(order)
        return {"order": order, "payment_provider": "payfast", **checkout}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/payfast/notify")
async def payfast_itn(request: Request, background_tasks: BackgroundTasks,
                      payment_service: PaymentService = Depends(get_payment_service)):
    """PayFast Instant Transaction Notification webhook."""
    form = await request.form()
    success = await payment_service.handle_itn(dict(form), background_tasks)
    if not success:
        raise HTTPException(400, "ITN validation failed")
    return {"status": "ok"}

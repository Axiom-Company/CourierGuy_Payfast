from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.order_service import OrderService
from app.services.email_service import EmailService
from app.api.deps import get_order_service, get_email_service, require_admin_api_key
from app.domain.enums import OrderStatus
from app.domain.schemas.order import OrderResponse, AdminStatusUpdate, AdminTrackingUpdate, AdminNotesUpdate

router = APIRouter(prefix="/orders", tags=["Orders"])


# Guest tracking (public — customer looks up by order number + email)
@router.get("/track/{order_number}")
async def track(order_number: str, email: str = Query(...),
                service: OrderService = Depends(get_order_service)):
    order = await service.get_by_order_number(order_number)
    if not order or (order.guest_email != email and (not order.customer or order.customer.email != email)):
        raise HTTPException(404, "Order not found")
    return order


# ── Admin (API-key auth from Elite TCG backend) ──

@router.get("/admin")
async def admin_list_orders(status: OrderStatus | None = None, page: int = Query(1, ge=1),
                            _=Depends(require_admin_api_key),
                            service: OrderService = Depends(get_order_service)):
    return await service.get_all_orders_admin(status, page)


@router.get("/admin/{order_id}")
async def admin_get_order(order_id: str, _=Depends(require_admin_api_key),
                          service: OrderService = Depends(get_order_service)):
    order = await service.get_by_id(order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return OrderResponse.model_validate(order)


@router.put("/admin/{order_id}/status")
async def admin_update_status(order_id: str, data: AdminStatusUpdate,
                              _=Depends(require_admin_api_key),
                              service: OrderService = Depends(get_order_service),
                              email_service: EmailService = Depends(get_email_service)):
    order = await service.update_status(order_id, data.status)
    if not order:
        raise HTTPException(404, "Order not found")

    # Send email notifications for refund/cancel status changes
    to_email = order.guest_email or (order.customer.email if order.customer else "")
    to_name = order.guest_name or (order.customer.name if order.customer else "Customer")
    if to_email:
        if data.status == OrderStatus.REFUNDED:
            await email_service.send_refund_confirmation(
                to_email, to_name, order.order_number,
                order.total_zar, "Original payment method",
            )
        elif data.status == OrderStatus.CANCELLED:
            await email_service.send_order_cancelled(
                to_email, to_name, order.order_number, order.total_zar,
            )

    return {"status": "ok"}


@router.put("/admin/{order_id}/tracking")
async def admin_add_tracking(order_id: str, data: AdminTrackingUpdate,
                             _=Depends(require_admin_api_key),
                             service: OrderService = Depends(get_order_service),
                             email_service: EmailService = Depends(get_email_service)):
    order = await service.add_tracking(order_id, data.tracking_number)
    if not order:
        raise HTTPException(404, "Order not found")

    # Send shipping notification email
    to_email = order.guest_email or (order.customer.email if order.customer else "")
    to_name = order.guest_name or (order.customer.name if order.customer else "Customer")
    if to_email:
        tracking_url = f"https://www.thecourierguy.co.za/tracking?waybill={data.tracking_number}"
        await email_service.send_shipping_notification(
            to_email, to_name, order.order_number,
            data.tracking_number, "The Courier Guy", tracking_url,
        )

    return {"status": "ok"}


@router.put("/admin/{order_id}/notes")
async def admin_update_notes(order_id: str, data: AdminNotesUpdate,
                             _=Depends(require_admin_api_key),
                             service: OrderService = Depends(get_order_service)):
    order = await service.update_notes(order_id, data.notes)
    if not order:
        raise HTTPException(404, "Order not found")
    return {"status": "ok"}

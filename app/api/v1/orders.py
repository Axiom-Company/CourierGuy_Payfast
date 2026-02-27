from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.order_service import OrderService
from app.api.deps import get_order_service, get_current_user, require_seller, require_admin_api_key
from app.domain.models.user import User
from app.domain.enums import OrderStatus
from app.domain.schemas.order import OrderResponse, AdminStatusUpdate, AdminTrackingUpdate, AdminNotesUpdate

router = APIRouter(prefix="/orders", tags=["Orders"])


# Customer
@router.get("/my")
async def my_orders(page: int = Query(1, ge=1), user: User = Depends(get_current_user),
                    service: OrderService = Depends(get_order_service)):
    return await service.get_customer_orders(user.id, page)


@router.get("/my/{order_number}")
async def my_order(order_number: str, user: User = Depends(get_current_user),
                   service: OrderService = Depends(get_order_service)):
    order = await service.get_by_order_number(order_number)
    if not order or order.customer_id != user.id:
        raise HTTPException(404, "Order not found")
    return order


# Guest tracking
@router.get("/track/{order_number}")
async def track(order_number: str, email: str = Query(...),
                service: OrderService = Depends(get_order_service)):
    order = await service.get_by_order_number(order_number)
    if not order or (order.guest_email != email and (not order.customer or order.customer.email != email)):
        raise HTTPException(404, "Order not found")
    return order


# Seller
@router.get("/manage")
async def all_orders(status: OrderStatus | None = None, page: int = Query(1, ge=1),
                     user: User = Depends(require_seller),
                     service: OrderService = Depends(get_order_service)):
    return await service.get_all_orders(status, page)


@router.put("/manage/{order_id}/status")
async def update_status(order_id: str, status: OrderStatus,
                        user: User = Depends(require_seller),
                        service: OrderService = Depends(get_order_service)):
    return await service.update_status(order_id, status)


@router.put("/manage/{order_id}/tracking")
async def add_tracking(order_id: str, tracking_number: str,
                       user: User = Depends(require_seller),
                       service: OrderService = Depends(get_order_service)):
    return await service.add_tracking(order_id, tracking_number)


# ── Admin (API-key auth from Elite TCG admin panel) ──

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
                              service: OrderService = Depends(get_order_service)):
    order = await service.update_status(order_id, data.status)
    if not order:
        raise HTTPException(404, "Order not found")
    return {"status": "ok"}


@router.put("/admin/{order_id}/tracking")
async def admin_add_tracking(order_id: str, data: AdminTrackingUpdate,
                             _=Depends(require_admin_api_key),
                             service: OrderService = Depends(get_order_service)):
    order = await service.add_tracking(order_id, data.tracking_number)
    if not order:
        raise HTTPException(404, "Order not found")
    return {"status": "ok"}


@router.put("/admin/{order_id}/notes")
async def admin_update_notes(order_id: str, data: AdminNotesUpdate,
                             _=Depends(require_admin_api_key),
                             service: OrderService = Depends(get_order_service)):
    order = await service.update_notes(order_id, data.notes)
    if not order:
        raise HTTPException(404, "Order not found")
    return {"status": "ok"}

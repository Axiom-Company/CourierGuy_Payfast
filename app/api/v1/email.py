from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.email_service import EmailService
from app.api.deps import get_email_service, require_admin, get_current_user_id
from app.domain.models.user import Profile
from app.database import get_db
from app.domain.schemas.email import (
    EmailResponse, WelcomeEmailRequest, OrderConfirmationRequest,
    ShippingNotificationRequest, DeliveryConfirmationRequest,
    PaymentFailedRequest, RefundConfirmationRequest, OrderCancelledRequest,
    BackInStockRequest, AbandonedCartRequest, NewDropAlertRequest,
    NotificationPreferenceUpdate, NotificationPreferenceResponse,
)
from app.domain.models.notification_preference import NotificationPreference

router = APIRouter(prefix="/email", tags=["Email"])


# ── Admin-triggered email endpoints ──────────────────────────────────────────

@router.post("/welcome", response_model=EmailResponse)
async def send_welcome(data: WelcomeEmailRequest, admin: Profile = Depends(require_admin),
                        email: EmailService = Depends(get_email_service)):
    await email.send_welcome_email(data.to_email, data.to_name)
    return EmailResponse(success=True, message="Welcome email queued")


@router.post("/order-confirmation", response_model=EmailResponse)
async def send_order_confirmation(data: OrderConfirmationRequest, admin: Profile = Depends(require_admin),
                                   email: EmailService = Depends(get_email_service)):
    await email.send_order_confirmation(
        data.to_email, data.to_name, data.order_id, data.order_items,
        data.subtotal, data.shipping_cost, data.total, data.shipping_address, data.order_date,
    )
    return EmailResponse(success=True, message="Order confirmation email queued")


@router.post("/shipping-notification", response_model=EmailResponse)
async def send_shipping(data: ShippingNotificationRequest, admin: Profile = Depends(require_admin),
                         email: EmailService = Depends(get_email_service)):
    await email.send_shipping_notification(
        data.to_email, data.to_name, data.order_id,
        data.tracking_number, data.courier, data.tracking_url,
    )
    return EmailResponse(success=True, message="Shipping notification email queued")


@router.post("/delivery-confirmation", response_model=EmailResponse)
async def send_delivery(data: DeliveryConfirmationRequest, admin: Profile = Depends(require_admin),
                         email: EmailService = Depends(get_email_service)):
    await email.send_delivery_confirmation(data.to_email, data.to_name, data.order_id)
    return EmailResponse(success=True, message="Delivery confirmation email queued")


@router.post("/payment-failed", response_model=EmailResponse)
async def send_payment_failed(data: PaymentFailedRequest, admin: Profile = Depends(require_admin),
                               email: EmailService = Depends(get_email_service)):
    await email.send_payment_failed(data.to_email, data.to_name, data.order_id, data.retry_url)
    return EmailResponse(success=True, message="Payment failed email queued")


@router.post("/refund-confirmation", response_model=EmailResponse)
async def send_refund(data: RefundConfirmationRequest, admin: Profile = Depends(require_admin),
                       email: EmailService = Depends(get_email_service)):
    await email.send_refund_confirmation(
        data.to_email, data.to_name, data.order_id, data.refund_amount, data.refund_method,
    )
    return EmailResponse(success=True, message="Refund confirmation email queued")


@router.post("/order-cancelled", response_model=EmailResponse)
async def send_cancelled(data: OrderCancelledRequest, admin: Profile = Depends(require_admin),
                          email: EmailService = Depends(get_email_service)):
    await email.send_order_cancelled(data.to_email, data.to_name, data.order_id, data.refund_amount)
    return EmailResponse(success=True, message="Order cancelled email queued")


@router.post("/back-in-stock", response_model=EmailResponse)
async def send_back_in_stock(data: BackInStockRequest, admin: Profile = Depends(require_admin),
                              email: EmailService = Depends(get_email_service)):
    await email.send_back_in_stock(
        data.to_email, data.to_name, data.product_name,
        data.product_price, data.product_url, data.user_id,
    )
    return EmailResponse(success=True, message="Back in stock email queued")


@router.post("/abandoned-cart", response_model=EmailResponse)
async def send_abandoned_cart(data: AbandonedCartRequest, admin: Profile = Depends(require_admin),
                               email: EmailService = Depends(get_email_service)):
    await email.send_abandoned_cart(
        data.to_email, data.to_name, data.cart_items, data.cart_url, data.user_id,
    )
    return EmailResponse(success=True, message="Abandoned cart email queued")


@router.post("/new-drop-alert", response_model=EmailResponse)
async def send_new_drop(data: NewDropAlertRequest, admin: Profile = Depends(require_admin),
                         email: EmailService = Depends(get_email_service)):
    await email.send_new_drop_alert(
        data.to_email, data.to_name, data.set_name,
        data.set_description, data.drop_url, data.user_id,
    )
    return EmailResponse(success=True, message="New drop alert email queued")


# ── User notification preferences ─────────────────────────────────────────────

@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_preferences(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        return NotificationPreferenceResponse(
            order_updates=True, marketing_emails=True,
            restock_alerts=True, new_drops=True,
        )
    return NotificationPreferenceResponse(
        order_updates=pref.order_updates,
        marketing_emails=pref.marketing_emails,
        restock_alerts=pref.restock_alerts,
        new_drops=pref.new_drops,
    )


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_preferences(
    data: NotificationPreferenceUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NotificationPreference).where(NotificationPreference.user_id == user_id)
    )
    pref = result.scalar_one_or_none()

    if not pref:
        pref = NotificationPreference(user_id=user_id)
        db.add(pref)

    if data.order_updates is not None:
        pref.order_updates = data.order_updates
    if data.marketing_emails is not None:
        pref.marketing_emails = data.marketing_emails
    if data.restock_alerts is not None:
        pref.restock_alerts = data.restock_alerts
    if data.new_drops is not None:
        pref.new_drops = data.new_drops

    await db.flush()

    return NotificationPreferenceResponse(
        order_updates=pref.order_updates,
        marketing_emails=pref.marketing_emails,
        restock_alerts=pref.restock_alerts,
        new_drops=pref.new_drops,
    )

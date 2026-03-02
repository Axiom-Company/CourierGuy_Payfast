from pydantic import BaseModel, EmailStr


class EmailResponse(BaseModel):
    success: bool
    message: str


# ── Request models ────────────────────────────────────────────────────────────

class WelcomeEmailRequest(BaseModel):
    to_email: EmailStr
    to_name: str


class OrderConfirmationRequest(BaseModel):
    to_email: EmailStr
    to_name: str
    order_id: str
    order_items: list[dict]
    subtotal: float
    shipping_cost: float
    total: float
    shipping_address: str
    order_date: str


class ShippingNotificationRequest(BaseModel):
    to_email: EmailStr
    to_name: str
    order_id: str
    tracking_number: str
    courier: str = "The Courier Guy"
    tracking_url: str = ""


class DeliveryConfirmationRequest(BaseModel):
    to_email: EmailStr
    to_name: str
    order_id: str


class PaymentFailedRequest(BaseModel):
    to_email: EmailStr
    to_name: str
    order_id: str
    retry_url: str


class RefundConfirmationRequest(BaseModel):
    to_email: EmailStr
    to_name: str
    order_id: str
    refund_amount: float
    refund_method: str


class OrderCancelledRequest(BaseModel):
    to_email: EmailStr
    to_name: str
    order_id: str
    refund_amount: float = 0.0


class BackInStockRequest(BaseModel):
    to_email: EmailStr
    to_name: str
    product_name: str
    product_price: float
    product_url: str
    user_id: str | None = None


class AbandonedCartRequest(BaseModel):
    to_email: EmailStr
    to_name: str
    cart_items: list[dict]
    cart_url: str
    user_id: str | None = None


class NewDropAlertRequest(BaseModel):
    to_email: EmailStr
    to_name: str
    set_name: str
    set_description: str
    drop_url: str
    user_id: str | None = None


# ── Notification preference models ───────────────────────────────────────────

class NotificationPreferenceUpdate(BaseModel):
    order_updates: bool | None = None
    marketing_emails: bool | None = None
    restock_alerts: bool | None = None
    new_drops: bool | None = None


class NotificationPreferenceResponse(BaseModel):
    order_updates: bool
    marketing_emails: bool
    restock_alerts: bool
    new_drops: bool


# ── Admin email log / webhook response models ────────────────────────────────

class EmailLogItem(BaseModel):
    id: str
    user_email: str
    email_type: str
    subject: str
    status: str
    error_message: str | None = None
    sent_at: str


class EmailLogsResponse(BaseModel):
    logs: list[EmailLogItem]
    total: int
    page: int
    page_size: int


class WebhookEventItem(BaseModel):
    id: str
    event_type: str
    recipient_email: str
    subject: str | None = None
    email_reference: str | None = None
    bounce_type: str | None = None
    bounce_reason: str | None = None
    received_at: str


class WebhookEventsResponse(BaseModel):
    events: list[WebhookEventItem]
    total: int
    page: int
    page_size: int


class EmailStatsResponse(BaseModel):
    total_sent: int
    total_failed: int
    total_bounces: int
    total_soft_bounces: int
    total_hard_bounces: int
    total_opens: int
    total_clicks: int
    bounce_rate: float
    open_rate: float
    click_rate: float

from pydantic import BaseModel
from app.domain.enums import OrderStatus, PaymentStatus, ShippingMethod


class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    product_type: str
    condition: str | None
    quantity: int
    unit_price_zar: float
    line_total_zar: float
    photo_url: str | None
    tcg_image_small: str | None

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: str
    order_number: str
    order_status: OrderStatus
    payment_status: PaymentStatus
    shipping_method: ShippingMethod
    shipping_cost_zar: float
    subtotal_zar: float
    total_zar: float
    courier_tracking_number: str | None
    courier_booking_reference: str | None
    shipping_address_line1: str | None
    shipping_city: str | None
    shipping_province: str | None
    shipping_postal_code: str | None
    guest_email: str | None
    guest_name: str | None
    items: list[OrderItemResponse]
    seller_notes: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Lightweight order for list views."""
    id: str
    order_number: str
    order_status: OrderStatus
    payment_status: PaymentStatus
    total_zar: float
    item_count: int
    shipping_method: ShippingMethod
    created_at: str

    class Config:
        from_attributes = True


# ── Admin request bodies ──

class AdminStatusUpdate(BaseModel):
    status: OrderStatus


class AdminTrackingUpdate(BaseModel):
    tracking_number: str


class AdminNotesUpdate(BaseModel):
    notes: str

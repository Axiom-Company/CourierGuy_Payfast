from __future__ import annotations

from pydantic import BaseModel


class ShippingAddressSchema(BaseModel):
    line1: str
    line2: str | None = None
    city: str
    province: str
    postal_code: str
    country: str = "South Africa"


class MarketplaceCreatePaymentRequest(BaseModel):
    listing_id: str
    quantity: int = 1
    buyer_email: str
    buyer_name: str
    buyer_phone: str | None = None
    shipping_address: ShippingAddressSchema | None = None


class MarketplaceOrderResponse(BaseModel):
    id: str
    order_number: str
    total_amount: float
    status: str
    payment_status: str
    created_at: str
    paid_at: str | None = None
    listing_title: str | None = None
    listing_images: str | None = None


class PromotionTier(BaseModel):
    label: str
    days: int
    price: float
    sort_priority: int


class PurchasePromotionRequest(BaseModel):
    listing_id: str
    tier: str

from pydantic import BaseModel, EmailStr
from app.domain.enums import ShippingMethod


class CheckoutRequest(BaseModel):
    # Guest info (required if not logged in)
    email: EmailStr | None = None
    full_name: str | None = None
    phone: str | None = None

    # Shipping
    shipping_method: ShippingMethod
    shipping_address_line1: str | None = None
    shipping_address_line2: str | None = None
    shipping_city: str | None = None
    shipping_province: str | None = None
    shipping_postal_code: str | None = None
    shipping_cost_zar: float = 0.0


class CheckoutResponse(BaseModel):
    order: dict  # OrderResponse
    payment_url: str
    payment_data: dict  # Form fields to POST to PayFast

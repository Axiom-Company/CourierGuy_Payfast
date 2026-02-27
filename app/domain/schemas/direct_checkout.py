from pydantic import BaseModel, EmailStr, Field
from app.domain.enums import ShippingMethod


class DirectCheckoutItem(BaseModel):
    product_id: str
    name: str
    quantity: int = Field(..., ge=1)
    unit_price_zar: float = Field(..., gt=0)
    image_url: str | None = None


class DirectCheckoutCustomer(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=10)


class DirectCheckoutShipping(BaseModel):
    method: ShippingMethod
    address_line1: str = Field(..., min_length=1)
    address_line2: str | None = None
    city: str = Field(..., min_length=1)
    province: str = Field(..., min_length=1)
    postal_code: str = Field(..., min_length=4, max_length=5)
    cost_zar: float = 0.0


class DirectCheckoutRequest(BaseModel):
    items: list[DirectCheckoutItem] = Field(..., min_length=1)
    customer: DirectCheckoutCustomer
    shipping: DirectCheckoutShipping

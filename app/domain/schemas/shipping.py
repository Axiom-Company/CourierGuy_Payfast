from pydantic import BaseModel, Field


class ShippingQuoteRequest(BaseModel):
    address_line1: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    province: str = Field(..., min_length=1)
    postal_code: str = Field(..., min_length=4, max_length=5)
    total_weight_grams: int | None = None  # Auto-calculated from cart if None


class ShippingQuoteResponse(BaseModel):
    courier_cost_zar: float
    customer_cost_zar: float
    handling_fee_zar: float
    estimated_days: int
    service_name: str


class ShipmentBookRequest(BaseModel):
    order_id: str


class ShipmentBookResponse(BaseModel):
    tracking_number: str
    booking_reference: str
    collection_date: str
    tracking_url: str


class CourierGuyWebhookPayload(BaseModel):
    tracking_number: str
    status: str
    timestamp: str
    description: str | None = None

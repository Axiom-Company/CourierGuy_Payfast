"""
Payflex Pydantic models.

All money amounts use Decimal — never float — for financial accuracy.
Models use extra="ignore" so unknown fields from Payflex don't crash the app.
"""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PayflexOrderStatus(str, Enum):
    """Statuses Payflex may report for an order."""
    PENDING = "Pending"
    APPROVED = "Approved"
    DECLINED = "Declined"
    CANCELLED = "Cancelled"
    EXPIRED = "Expired"
    UNKNOWN = "Unknown"


# ---------------------------------------------------------------------------
# Shared / Error models
# ---------------------------------------------------------------------------

class PaymentErrorResponse(BaseModel):
    """Consistent error format returned to the frontend."""
    success: bool = False
    error_code: str = Field(..., description="Machine-readable error code")
    error_message: str = Field(..., description="Human-readable message safe to show customers")
    detail: str | None = Field(None, description="Technical detail for logging — never show to customer")
    provider: str = "payflex"
    order_id: str | None = None
    retry_allowed: bool = False
    fallback_available: bool = True


# ---------------------------------------------------------------------------
# Address models
# ---------------------------------------------------------------------------

class PayflexAddress(BaseModel):
    """Address block expected by Payflex Place Order."""
    model_config = ConfigDict(extra="ignore")

    name: str = ""
    line1: str = ""
    line2: str = ""
    suburb: str = ""
    city: str = ""
    postcode: str = ""
    region: str = ""
    country: str = "ZA"
    phone: str = ""


# ---------------------------------------------------------------------------
# Line item
# ---------------------------------------------------------------------------

class PayflexLineItem(BaseModel):
    """Single line item for a Payflex order."""
    model_config = ConfigDict(extra="ignore")

    name: str
    quantity: int = Field(..., ge=1)
    price: Decimal = Field(..., ge=Decimal("0.01"), description="Unit price in ZAR")

    @field_validator("price", mode="before")
    @classmethod
    def coerce_price(cls, v):
        return Decimal(str(v))


# ---------------------------------------------------------------------------
# Amount breakdown
# ---------------------------------------------------------------------------

class PayflexAmount(BaseModel):
    """Amount breakdown for a Payflex order."""
    model_config = ConfigDict(extra="ignore")

    amount: Decimal = Field(..., gt=Decimal("0"), description="Total order amount in ZAR")
    currency: str = "ZAR"
    shipping: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    tax: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    discount: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))

    @field_validator("amount", "shipping", "tax", "discount", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        return Decimal(str(v))


# ---------------------------------------------------------------------------
# Consumer (customer details sent to Payflex)
# ---------------------------------------------------------------------------

class PayflexConsumer(BaseModel):
    """Customer details for Payflex."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    email: EmailStr
    givenNames: str = Field(..., min_length=1, alias="given_names")
    surname: str = Field(..., min_length=1)
    phoneNumber: str = Field("", alias="phone_number")


# ---------------------------------------------------------------------------
# Request: What our frontend sends to our backend
# ---------------------------------------------------------------------------

class PayflexCreateOrderRequest(BaseModel):
    """Request from our frontend to initiate Payflex checkout."""
    order_id: str = Field(..., description="Our internal order ID or order number")


# ---------------------------------------------------------------------------
# Payload: What we send TO the Payflex API
# ---------------------------------------------------------------------------

class PayflexCreateOrderPayload(BaseModel):
    """Payload we POST to Payflex's /order endpoint."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    consumer: dict
    orderDetails: dict = Field(alias="order_details")
    billing: dict = {}
    shipping: dict = {}
    amount: dict
    merchant: dict = {}
    redirectUrl: str = Field(..., alias="redirect_url")
    statusCallbackUrl: str = Field(..., alias="status_callback_url")


# ---------------------------------------------------------------------------
# Response: What Payflex returns from POST /order
# ---------------------------------------------------------------------------

class PayflexCreateOrderResponse(BaseModel):
    """Response from Payflex after creating an order."""
    model_config = ConfigDict(extra="ignore")

    token: str
    expiryDateTime: str | None = Field(None, alias="expiryDateTime")
    redirectUrl: str = Field(..., alias="redirectUrl")
    orderId: str = Field(..., alias="orderId")


# ---------------------------------------------------------------------------
# Response: What Payflex returns from GET /order/{orderId}
# ---------------------------------------------------------------------------

class PayflexOrderStatusResponse(BaseModel):
    """Response from Payflex GET /order/{orderId} and webhook payload."""
    model_config = ConfigDict(extra="ignore")

    orderId: str = Field("", alias="orderId")
    orderStatus: str = Field("", alias="orderStatus")
    token: str = ""
    amount: Decimal | None = None
    currency: str = "ZAR"

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount(cls, v):
        if v is None:
            return None
        return Decimal(str(v))


# ---------------------------------------------------------------------------
# Webhook payload (mirrors GET /order response)
# ---------------------------------------------------------------------------

class PayflexWebhookPayload(BaseModel):
    """Payload Payflex POSTs to our statusCallbackUrl."""
    model_config = ConfigDict(extra="ignore")

    orderId: str = Field("", alias="orderId")
    orderStatus: str = Field("", alias="orderStatus")
    token: str = ""
    amount: Decimal | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount(cls, v):
        if v is None:
            return None
        return Decimal(str(v))


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------

class PayflexRefundRequest(BaseModel):
    """Refund request — amount in ZAR."""
    amount: Decimal = Field(..., gt=Decimal("0"), description="Refund amount in ZAR")

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount(cls, v):
        return Decimal(str(v))


class PayflexRefundResponse(BaseModel):
    """Response from Payflex POST /order/{orderId}/refund."""
    model_config = ConfigDict(extra="ignore")

    refundId: str = Field("", alias="refundId")
    orderId: str = Field("", alias="orderId")
    amount: Decimal | None = None
    status: str = ""

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount(cls, v):
        if v is None:
            return None
        return Decimal(str(v))


# ---------------------------------------------------------------------------
# Configuration (from GET /configuration)
# ---------------------------------------------------------------------------

class PayflexConfigResponse(BaseModel):
    """Response from Payflex GET /configuration."""
    model_config = ConfigDict(extra="ignore")

    minimumAmount: Decimal = Field(Decimal("0"), alias="minimumAmount")
    maximumAmount: Decimal = Field(Decimal("0"), alias="maximumAmount")

    @field_validator("minimumAmount", "maximumAmount", mode="before")
    @classmethod
    def coerce_decimal(cls, v):
        return Decimal(str(v))


# ---------------------------------------------------------------------------
# Frontend-facing responses
# ---------------------------------------------------------------------------

class PayflexCheckoutResponse(BaseModel):
    """Returned to our frontend after successfully creating a Payflex order."""
    success: bool = True
    redirect_url: str
    payflex_order_id: str
    token: str
    expires_at: str | None = None


class PayflexOrderStatusPublic(BaseModel):
    """Order status returned to our frontend (from return page or polling)."""
    order_id: str
    order_number: str
    payflex_order_id: str | None = None
    status: str
    payment_status: str
    total_zar: str
    provider: str = "payflex"


class PayflexConfigPublic(BaseModel):
    """Public Payflex configuration for the frontend."""
    available: bool
    min_amount: str = "0.00"
    max_amount: str = "0.00"

"""
Shared payment schemas used across payment providers.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PaymentErrorResponse(BaseModel):
    """Consistent error response format for all payment providers."""
    success: bool = False
    error_code: str = Field(..., description="Machine-readable error code")
    error_message: str = Field(..., description="Human-readable message safe to show customers")
    detail: str | None = Field(None, description="Technical detail for logging — never show to customer")
    provider: str
    order_id: str | None = None
    retry_allowed: bool = False
    fallback_available: bool = True


# Error code registry
PAYFLEX_ERRORS = {
    "PAYFLEX_AUTH_FAILED": "Payment service temporarily unavailable. Please try PayFast or try again later.",
    "PAYFLEX_ORDER_CREATE_FAILED": "We couldn't start your payment. Please try again.",
    "PAYFLEX_ORDER_DECLINED": "Your Payflex application was not approved. You can still pay with PayFast.",
    "PAYFLEX_ORDER_CANCELLED": "Payment was cancelled. Your cart is still saved.",
    "PAYFLEX_ORDER_EXPIRED": "Your payment session has expired. Please start checkout again.",
    "PAYFLEX_AMOUNT_OUT_OF_RANGE": "Payflex is not available for this order amount. Please use PayFast.",
    "PAYFLEX_SERVICE_UNAVAILABLE": "Payflex is temporarily unavailable. Please use PayFast.",
    "PAYFLEX_WEBHOOK_INVALID": "Webhook validation failed.",
    "PAYFLEX_REFUND_FAILED": "We couldn't process your refund. Our team has been notified.",
    "PAYFLEX_AMOUNT_MISMATCH": "Amount mismatch detected — flagged for manual review.",
    "PAYFLEX_UNKNOWN_ERROR": "Something went wrong. Please contact support@elitetcg.co.za.",
    "PAYFLEX_ALREADY_PAID": "This order has already been paid.",
    "PAYFLEX_ORDER_NOT_FOUND": "Order not found.",
}


def make_payflex_error(
    code: str,
    *,
    detail: str | None = None,
    order_id: str | None = None,
    retry_allowed: bool = False,
) -> PaymentErrorResponse:
    """Build a PaymentErrorResponse from an error code."""
    return PaymentErrorResponse(
        error_code=code,
        error_message=PAYFLEX_ERRORS.get(code, PAYFLEX_ERRORS["PAYFLEX_UNKNOWN_ERROR"]),
        detail=detail,
        provider="payflex",
        order_id=order_id,
        retry_allowed=retry_allowed,
    )

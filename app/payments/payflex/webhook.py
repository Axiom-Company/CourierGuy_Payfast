"""
Payflex webhook handler.

Security rules:
1. NEVER trust the webhook payload alone for financial state changes.
2. ALWAYS re-fetch the order from Payflex GET /order/{id} to verify.
3. ALWAYS verify the order exists in our database before updating.
4. Handle duplicate callbacks idempotently.
5. Compare amounts — flag mismatches for manual review.
6. Return 200 immediately; do heavy processing in the background.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from app.payments.payflex.client import PayflexClient
from app.payments.payflex.schemas import PayflexWebhookPayload, PayflexOrderStatus
from app.repositories.order_repo import OrderRepository
from app.services.telegram_service import TelegramService
from app.domain.enums import PaymentStatus, OrderStatus

logger = logging.getLogger(__name__)

# Map Payflex status strings to our internal enums
_STATUS_MAP = {
    "Approved": (PaymentStatus.COMPLETE, OrderStatus.PAID),
    "Declined": (PaymentStatus.FAILED, OrderStatus.CANCELLED),
    "Cancelled": (PaymentStatus.CANCELLED, OrderStatus.CANCELLED),
    "Expired": (PaymentStatus.CANCELLED, OrderStatus.CANCELLED),
}


class PayflexWebhookHandler:
    """Processes incoming Payflex status callback webhooks."""

    def __init__(
        self,
        payflex_client: PayflexClient,
        order_repo: OrderRepository,
        telegram: TelegramService | None = None,
    ):
        self._client = payflex_client
        self._order_repo = order_repo
        self._telegram = telegram or TelegramService()

    async def handle(self, payload: PayflexWebhookPayload) -> dict:
        """
        Process a Payflex webhook callback.

        Steps:
        1. Log the full payload for audit trail.
        2. Find the order in our database by payflex_order_id.
        3. Check for idempotency — skip if already in the target status.
        4. Re-fetch order status from Payflex API to verify independently.
        5. Compare amounts.
        6. Update our order status.

        Returns a dict with processing result for logging.
        """
        payflex_order_id = payload.orderId
        reported_status = payload.orderStatus

        logger.info(
            "Payflex webhook received: orderId=%s status=%s amount=%s",
            payflex_order_id, reported_status, payload.amount,
        )

        # 1. Find our order by payflex_order_id
        order = await self._order_repo.get_by_payflex_order_id(payflex_order_id)
        if order is None:
            logger.error("Payflex webhook: no order found for payflex_order_id=%s", payflex_order_id)
            return {"processed": False, "reason": "order_not_found"}

        # 2. Idempotency check — already in a terminal state for this status?
        target = _STATUS_MAP.get(reported_status)
        if target and order.payment_status == target[0]:
            logger.info(
                "Payflex webhook: order %s already in status %s — skipping (idempotent)",
                order.order_number, order.payment_status,
            )
            return {"processed": True, "reason": "already_processed"}

        # 3. Re-fetch from Payflex to verify (NEVER trust webhook payload alone)
        try:
            verified = await self._client.get_order(payflex_order_id)
        except Exception as exc:
            logger.error(
                "Payflex webhook: failed to verify order %s from API: %s",
                payflex_order_id, exc,
            )
            # Still return 200 so Payflex doesn't retry endlessly — we'll reconcile later
            return {"processed": False, "reason": "verification_failed"}

        verified_status = verified.orderStatus
        logger.info(
            "Payflex webhook: verified status for %s = %s (webhook reported %s)",
            payflex_order_id, verified_status, reported_status,
        )

        # 4. Amount mismatch check
        if verified.amount is not None:
            our_total = Decimal(str(order.total_zar))
            if abs(verified.amount - our_total) > Decimal("0.01"):
                logger.error(
                    "AMOUNT MISMATCH: order %s — our total R%s vs Payflex R%s. Flagging for manual review.",
                    order.order_number, our_total, verified.amount,
                )
                await self._order_repo.update_by_id(order.id, {
                    "seller_notes": (
                        f"PAYFLEX AMOUNT MISMATCH: Our total R{our_total}, "
                        f"Payflex reported R{verified.amount}. Manual review required."
                    ),
                })
                return {"processed": False, "reason": "amount_mismatch"}

        # 5. Update order status based on verified status
        target = _STATUS_MAP.get(verified_status)
        if target is None:
            logger.warning(
                "Payflex webhook: unrecognized status '%s' for order %s",
                verified_status, order.order_number,
            )
            return {"processed": False, "reason": "unknown_status"}

        payment_status, order_status = target
        update_data: dict = {
            "payment_status": payment_status,
            "order_status": order_status,
        }

        if payment_status == PaymentStatus.COMPLETE:
            update_data["payflex_payment_id"] = payflex_order_id

        await self._order_repo.update_by_id(order.id, update_data)

        logger.info(
            "Payflex webhook: order %s updated to payment_status=%s, order_status=%s",
            order.order_number, payment_status, order_status,
        )

        # Telegram notification for paid orders (best effort)
        if payment_status == PaymentStatus.COMPLETE:
            try:
                email = order.guest_email or (order.customer.email if order.customer else "")
                await self._telegram.notify_order_paid(
                    order.order_number, float(order.total_zar), email,
                )
            except Exception:
                pass  # best effort

        return {
            "processed": True,
            "order_number": order.order_number,
            "payment_status": payment_status.value,
            "order_status": order_status.value,
        }

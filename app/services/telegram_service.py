"""Telegram Bot notification service for Elite TCG (elitetcgbot)."""
import logging
import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


class TelegramService:
    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token
        self.chat_id = chat_id

    async def _send(self, text: str, parse_mode: str = "HTML") -> None:
        if not self.bot_token or not self.chat_id:
            logger.warning("[TELEGRAM] Bot not configured, skipping notification")
            return

        url = f"{TELEGRAM_API}/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=10)

            if resp.status_code >= 400:
                logger.error(f"[TELEGRAM] API error {resp.status_code}: {resp.text}")
                return

            logger.info("[TELEGRAM] Notification sent")
        except Exception as e:
            logger.error(f"[TELEGRAM] Failed to send: {e}")

    # ── Checkout / Store Orders ──

    async def notify_order_paid(self, order_number: str, total_zar: float, customer_email: str) -> None:
        text = (
            f"<b>💰 New Order Paid</b>\n\n"
            f"Order: <code>{order_number}</code>\n"
            f"Total: <b>R{total_zar:,.2f}</b>\n"
            f"Customer: {customer_email}"
        )
        await self._send(text)

    # ── Marketplace ──

    async def notify_marketplace_sale(
        self, order_number: str, listing_title: str, quantity: int,
        total_amount: float, seller_amount: float, buyer_email: str,
    ) -> None:
        text = (
            f"<b>🛒 Marketplace Sale</b>\n\n"
            f"Order: <code>{order_number}</code>\n"
            f"Item: {listing_title}\n"
            f"Qty: {quantity}\n"
            f"Total: <b>R{total_amount:,.2f}</b>\n"
            f"Seller receives: R{seller_amount:,.2f}\n"
            f"Buyer: {buyer_email}"
        )
        await self._send(text)

    async def notify_marketplace_delivery(self, order_number: str, seller_name: str) -> None:
        text = (
            f"<b>📦 Delivery Confirmed</b>\n\n"
            f"Order: <code>{order_number}</code>\n"
            f"Seller: {seller_name}"
        )
        await self._send(text)

    # ── Promotions ──

    async def notify_promotion_activated(
        self, listing_title: str, tier: str, seller_name: str, price_paid: float,
    ) -> None:
        text = (
            f"<b>⭐ Promotion Activated</b>\n\n"
            f"Listing: {listing_title}\n"
            f"Tier: {tier}\n"
            f"Paid: <b>R{price_paid:,.2f}</b>\n"
            f"Seller: {seller_name}"
        )
        await self._send(text)

    # ── Shipping ──

    async def notify_shipping_update(self, tracking_number: str, status: str, order_number: str = "") -> None:
        text = (
            f"<b>🚚 Shipping Update</b>\n\n"
            f"Tracking: <code>{tracking_number}</code>\n"
            f"Status: {status}"
        )
        if order_number:
            text += f"\nOrder: <code>{order_number}</code>"
        await self._send(text)

    async def notify_shipment_booked(self, order_number: str, tracking_number: str) -> None:
        text = (
            f"<b>📬 Shipment Booked</b>\n\n"
            f"Order: <code>{order_number}</code>\n"
            f"Tracking: <code>{tracking_number}</code>"
        )
        await self._send(text)

    # ── Generic ──

    async def send_test(self) -> None:
        await self._send("<b>✅ Elite TCG Bot Connected</b>\n\nelitetcgbot is working!")

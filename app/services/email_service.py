import logging
import httpx

from app.utils.email_templates import (
    ORDER_CONFIRMATION_TEMPLATE, SHIPPING_NOTIFICATION_TEMPLATE,
    SELLER_SALE_NOTIFICATION_TEMPLATE, SELLER_PAYOUT_NOTIFICATION_TEMPLATE,
    DELIVERY_CONFIRMED_SELLER_TEMPLATE, PROMOTION_CONFIRMATION_TEMPLATE,
)

logger = logging.getLogger(__name__)

ZEPTOMAIL_URL = "https://api.zeptomail.com/v1.1/email"


class EmailService:
    def __init__(self, api_key: str = "", from_email: str = "", from_name: str = "Elite TCG"):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name

    async def _send(self, to_email: str, to_name: str, subject: str, html_body: str) -> None:
        if not self.api_key:
            logger.warning(f"[EMAIL] ZeptoMail not configured, skipping send to {to_email}")
            return

        payload = {
            "from": {"address": self.from_email, "name": self.from_name},
            "to": [{"email_address": {"address": to_email, "name": to_name}}],
            "subject": subject,
            "htmlbody": html_body,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                ZEPTOMAIL_URL,
                json=payload,
                headers={
                    "Authorization": f"Zoho-enczapikey {self.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=15,
            )

        if resp.status_code >= 400:
            logger.error(f"[EMAIL] ZeptoMail error {resp.status_code}: {resp.text}")
            return

        logger.info(f"[EMAIL] Sent '{subject}' to {to_email}")

    async def send_order_confirmation(self, to_email: str, order_number: str, total_zar: float, to_name: str = "") -> None:
        try:
            html = ORDER_CONFIRMATION_TEMPLATE.format(order_number=order_number, total_zar=total_zar)
            await self._send(to_email, to_name, f"Order Confirmed — {order_number}", html)
        except Exception as e:
            logger.error(f"[EMAIL] Failed to send order confirmation to {to_email}: {e}")

    async def send_shipping_notification(self, to_email: str, order_number: str, tracking_number: str, to_name: str = "") -> None:
        try:
            tracking_url = f"https://www.thecourierguy.co.za/tracking?waybill={tracking_number}"
            html = SHIPPING_NOTIFICATION_TEMPLATE.format(
                order_number=order_number, tracking_number=tracking_number, tracking_url=tracking_url,
            )
            await self._send(to_email, to_name, f"Your Order Has Shipped — {order_number}", html)
        except Exception as e:
            logger.error(f"[EMAIL] Failed to send shipping notification to {to_email}: {e}")

    async def send_seller_sale_notification(
        self, to_email: str, seller_name: str, order_number: str,
        listing_title: str, quantity: int, seller_amount: float,
    ) -> None:
        try:
            html = SELLER_SALE_NOTIFICATION_TEMPLATE.format(
                seller_name=seller_name, listing_title=listing_title,
                quantity=quantity, seller_amount=seller_amount, order_number=order_number,
            )
            await self._send(to_email, seller_name, f"New Sale — {order_number}", html)
        except Exception as e:
            logger.error(f"[EMAIL] Failed to send seller sale notification to {to_email}: {e}")

    async def send_seller_payout_notification(
        self, to_email: str, seller_name: str, order_number: str, payout_amount: float,
    ) -> None:
        try:
            html = SELLER_PAYOUT_NOTIFICATION_TEMPLATE.format(
                seller_name=seller_name, order_number=order_number, payout_amount=payout_amount,
            )
            await self._send(to_email, seller_name, f"Payout Created — {order_number}", html)
        except Exception as e:
            logger.error(f"[EMAIL] Failed to send payout notification to {to_email}: {e}")

    async def send_delivery_confirmed_to_seller(
        self, to_email: str, seller_name: str, order_number: str,
    ) -> None:
        try:
            html = DELIVERY_CONFIRMED_SELLER_TEMPLATE.format(
                seller_name=seller_name, order_number=order_number,
            )
            await self._send(to_email, seller_name, f"Delivery Confirmed — {order_number}", html)
        except Exception as e:
            logger.error(f"[EMAIL] Failed to send delivery confirmation to {to_email}: {e}")

    async def send_promotion_confirmation(
        self, to_email: str, seller_name: str, listing_title: str, tier: str, expires_at: str,
    ) -> None:
        try:
            html = PROMOTION_CONFIRMATION_TEMPLATE.format(
                seller_name=seller_name, listing_title=listing_title, tier=tier, expires_at=expires_at,
            )
            await self._send(to_email, seller_name, f"Promotion Activated — {listing_title}", html)
        except Exception as e:
            logger.error(f"[EMAIL] Failed to send promotion confirmation to {to_email}: {e}")

    async def send_test(self, to_email: str, to_name: str = "") -> None:
        await self._send(to_email, to_name, "Elite TCG — Email Test", "<h2>ZeptoMail is working!</h2><p>This is a test email from Elite TCG.</p>")

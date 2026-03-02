import logging
from datetime import datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.email_templates import (
    SELLER_SALE_NOTIFICATION_TEMPLATE, SELLER_PAYOUT_NOTIFICATION_TEMPLATE,
    DELIVERY_CONFIRMED_SELLER_TEMPLATE, PROMOTION_CONFIRMATION_TEMPLATE,
    welcome_template, order_confirmation_template, shipping_notification_template,
    delivery_confirmation_template, payment_failed_template, refund_confirmation_template,
    order_cancelled_template, back_in_stock_template, abandoned_cart_template,
    new_drop_alert_template,
)

logger = logging.getLogger(__name__)

ZEPTOMAIL_URL = "https://api.zeptomail.com/v1.1/email"
ZEPTOMAIL_TEMPLATE_URL = "https://api.zeptomail.com/v1.1/email/template"

# ── ZeptoMail template keys (configured in ZeptoMail dashboard) ───────────────
TEMPLATE_KEYS = {
    "welcome": "2d6f.4c74624b3e468ae1.k1.eaca9620-15c2-11f1-8026-5254005934b4.19caba4d882",
    "order_receipt": "2d6f.4c74624b3e468ae1.k1.dad87c92-160e-11f1-8026-5254005934b4.19cad9682d2",
    "shipping_notification": "2d6f.4c74624b3e468ae1.k1.e62195f0-160e-11f1-8026-5254005934b4.19cad96cccf",
    "delivery_confirmed": "2d6f.4c74624b3e468ae1.k1.ef77e001-160e-11f1-8026-5254005934b4.19cad9709f8",
    "payment_failed": "2d6f.4c74624b3e468ae1.k1.fc960780-160e-11f1-8026-5254005934b4.19cad975ff8",
    "refund_confirmation": "2d6f.4c74624b3e468ae1.k1.08e657b0-160f-11f1-8026-5254005934b4.19cad97b0ab",
    "order_cancelled": "2d6f.4c74624b3e468ae1.k1.17d595b1-160f-11f1-8026-5254005934b4.19cad981281",
    "back_in_stock": "2d6f.4c74624b3e468ae1.k1.9da05640-160e-11f1-8026-5254005934b4.19cad94f1a4",
    "abandoned_cart": "2d6f.4c74624b3e468ae1.k1.8ffecdf1-160e-11f1-8026-5254005934b4.19cad949832",
    "new_drop_alert": "2d6f.4c74624b3e468ae1.k1.b7744680-160e-11f1-8026-5254005934b4.19cad959ae8",
    "email_verification": "2d6f.4c74624b3e468ae1.k1.1fc52e61-1610-11f1-8026-5254005934b4.19cad9ed43c",
    "password_reset": "2d6f.4c74624b3e468ae1.k1.113c2c41-1610-11f1-8026-5254005934b4.19cad9e74fd",
}


class EmailService:
    def __init__(
        self,
        api_key: str = "",
        from_email: str = "",
        from_name: str = "Elite TCG",
        bounce_email: str = "",
        db: AsyncSession | None = None,
    ):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
        self.bounce_email = bounce_email
        self.db = db

    # ── Core senders ──────────────────────────────────────────────────────────

    async def _send(self, to_email: str, to_name: str, subject: str, html_body: str) -> bool:
        """Send raw HTML email via ZeptoMail. Returns True on success."""
        if not self.api_key:
            logger.warning(f"[EMAIL] ZeptoMail not configured, skipping send to {to_email}")
            return False

        payload = {
            "from": {"address": self.from_email, "name": self.from_name},
            "to": [{"email_address": {"address": to_email, "name": to_name}}],
            "subject": subject,
            "htmlbody": html_body,
        }
        if self.bounce_email:
            payload["bounce_address"] = self.bounce_email

        try:
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
                await self._log(to_email, "raw", subject, "failed", resp.text)
                return False

            logger.info(f"[EMAIL] Sent '{subject}' to {to_email}")
            await self._log(to_email, "raw", subject, "sent")
            return True
        except Exception as e:
            logger.error(f"[EMAIL] Exception sending to {to_email}: {e}")
            await self._log(to_email, "raw", subject, "failed", str(e))
            return False

    async def _send_template(
        self, to_email: str, to_name: str, template_key: str,
        merge_info: dict, email_type: str, subject_hint: str = "",
    ) -> bool:
        """Send email via ZeptoMail template API. Returns True on success."""
        if not self.api_key:
            logger.warning(f"[EMAIL] ZeptoMail not configured, skipping template send to {to_email}")
            return False

        payload = {
            "template_key": template_key,
            "from": {"address": self.from_email, "name": self.from_name},
            "to": [{"email_address": {"address": to_email, "name": to_name}}],
            "merge_info": merge_info,
        }
        if self.bounce_email:
            payload["bounce_address"] = self.bounce_email

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    ZEPTOMAIL_TEMPLATE_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Zoho-enczapikey {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    timeout=15,
                )

            if resp.status_code >= 400:
                logger.error(f"[EMAIL] ZeptoMail template error {resp.status_code}: {resp.text}")
                await self._log(to_email, email_type, subject_hint, "failed", resp.text)
                return False

            logger.info(f"[EMAIL] Sent template '{email_type}' to {to_email}")
            await self._log(to_email, email_type, subject_hint, "sent")
            return True
        except Exception as e:
            logger.error(f"[EMAIL] Exception sending template to {to_email}: {e}")
            await self._log(to_email, email_type, subject_hint, "failed", str(e))
            return False

    # ── Email logging ─────────────────────────────────────────────────────────

    async def _log(
        self, user_email: str, email_type: str, subject: str,
        status: str, error_message: str | None = None,
    ) -> None:
        if not self.db:
            return
        try:
            import uuid
            from sqlalchemy import text
            await self.db.execute(
                text(
                    "INSERT INTO email_logs (id, user_email, email_type, subject, status, error_message) "
                    "VALUES (:id, :user_email, :email_type, :subject, :status, :error_message)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "user_email": user_email,
                    "email_type": email_type,
                    "subject": subject[:500],
                    "status": status,
                    "error_message": error_message,
                },
            )
        except Exception as e:
            logger.warning(f"[EMAIL] Failed to log email event: {e}")
            try:
                await self.db.rollback()
            except Exception:
                pass

    # ── Preference check ──────────────────────────────────────────────────────

    async def _check_preference(self, user_id: str | None, pref_field: str) -> bool:
        """Check notification preference. Returns True if allowed or no preference set."""
        if not user_id or not self.db:
            return True
        try:
            from sqlalchemy import select
            from app.domain.models.notification_preference import NotificationPreference
            result = await self.db.execute(
                select(NotificationPreference).where(NotificationPreference.user_id == user_id)
            )
            pref = result.scalar_one_or_none()
            if not pref:
                return True  # No preferences row = all enabled
            return getattr(pref, pref_field, True)
        except Exception as e:
            logger.warning(f"[EMAIL] Preference check failed: {e}")
            return True

    # ── Transactional emails (always send) ────────────────────────────────────

    async def send_welcome_email(self, to_email: str, to_name: str) -> None:
        try:
            await self._send_template(
                to_email, to_name,
                TEMPLATE_KEYS["welcome"],
                {"name": to_name},
                "welcome",
                f"Welcome to Elite TCG ⚡",
            )
        except Exception as e:
            logger.error(f"[EMAIL] Failed welcome email to {to_email}: {e}")

    async def send_order_confirmation(
        self, to_email: str, to_name: str, order_number: str,
        order_items: list[dict], subtotal: float, shipping_cost: float,
        total: float, shipping_address: str, order_date: str,
    ) -> None:
        try:
            # Build items HTML for template merge
            items_html = ""
            for item in order_items:
                items_html += (
                    f'<tr><td style="padding:10px 12px;border-bottom:1px solid #eee;">{item["name"]}</td>'
                    f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:center;">{item["quantity"]}</td>'
                    f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right;">R{item["unit_price"]:.2f}</td>'
                    f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right;">R{item["line_total"]:.2f}</td></tr>'
                )

            await self._send_template(
                to_email, to_name,
                TEMPLATE_KEYS["order_receipt"],
                {
                    "name": to_name,
                    "order_id": order_number,
                    "items_html": items_html,
                    "subtotal": f"R{subtotal:.2f}",
                    "shipping_cost": f"R{shipping_cost:.2f}",
                    "total": f"R{total:.2f}",
                    "shipping_address": shipping_address,
                    "order_date": order_date,
                },
                "order_confirmation",
                f"Order Confirmed — {order_number} ⚡",
            )
        except Exception as e:
            logger.error(f"[EMAIL] Failed order confirmation to {to_email}: {e}")

    async def send_shipping_notification(
        self, to_email: str, to_name: str, order_number: str,
        tracking_number: str, courier: str = "The Courier Guy",
        tracking_url: str = "",
    ) -> None:
        try:
            if not tracking_url:
                tracking_url = f"https://www.thecourierguy.co.za/tracking?waybill={tracking_number}"

            await self._send_template(
                to_email, to_name,
                TEMPLATE_KEYS["shipping_notification"],
                {
                    "name": to_name,
                    "order_id": order_number,
                    "tracking_number": tracking_number,
                    "courier": courier,
                    "tracking_url": tracking_url,
                },
                "shipping_notification",
                f"Your Order {order_number} Has Shipped! 📦",
            )
        except Exception as e:
            logger.error(f"[EMAIL] Failed shipping notification to {to_email}: {e}")

    async def send_delivery_confirmation(self, to_email: str, to_name: str, order_number: str) -> None:
        try:
            await self._send_template(
                to_email, to_name,
                TEMPLATE_KEYS["delivery_confirmed"],
                {"name": to_name, "order_id": order_number},
                "delivery_confirmation",
                f"Your Order {order_number} Has Arrived! ⚡",
            )
        except Exception as e:
            logger.error(f"[EMAIL] Failed delivery confirmation to {to_email}: {e}")

    async def send_payment_failed(
        self, to_email: str, to_name: str, order_number: str, retry_url: str,
    ) -> None:
        try:
            await self._send_template(
                to_email, to_name,
                TEMPLATE_KEYS["payment_failed"],
                {"name": to_name, "order_id": order_number, "retry_url": retry_url},
                "payment_failed",
                f"Payment Issue — Order {order_number}",
            )
        except Exception as e:
            logger.error(f"[EMAIL] Failed payment_failed email to {to_email}: {e}")

    async def send_refund_confirmation(
        self, to_email: str, to_name: str, order_number: str,
        refund_amount: float, refund_method: str,
    ) -> None:
        try:
            await self._send_template(
                to_email, to_name,
                TEMPLATE_KEYS["refund_confirmation"],
                {
                    "name": to_name,
                    "order_id": order_number,
                    "refund_amount": f"R{refund_amount:.2f}",
                    "refund_method": refund_method,
                },
                "refund_confirmation",
                f"Refund Processed — Order {order_number}",
            )
        except Exception as e:
            logger.error(f"[EMAIL] Failed refund confirmation to {to_email}: {e}")

    async def send_order_cancelled(
        self, to_email: str, to_name: str, order_number: str, refund_amount: float,
    ) -> None:
        try:
            await self._send_template(
                to_email, to_name,
                TEMPLATE_KEYS["order_cancelled"],
                {
                    "name": to_name,
                    "order_id": order_number,
                    "refund_amount": f"R{refund_amount:.2f}",
                },
                "order_cancelled",
                f"Order {order_number} Has Been Cancelled",
            )
        except Exception as e:
            logger.error(f"[EMAIL] Failed order cancelled email to {to_email}: {e}")

    # ── Marketing / optional emails (check preferences) ──────────────────────

    async def send_back_in_stock(
        self, to_email: str, to_name: str, product_name: str,
        product_price: float, product_url: str, user_id: str | None = None,
    ) -> None:
        try:
            if not await self._check_preference(user_id, "restock_alerts"):
                logger.info(f"[EMAIL] Skipping back_in_stock for {to_email} (preference off)")
                return
            await self._send_template(
                to_email, to_name,
                TEMPLATE_KEYS["back_in_stock"],
                {
                    "name": to_name,
                    "product_name": product_name,
                    "product_price": f"R{product_price:.2f}",
                    "product_url": product_url,
                },
                "back_in_stock",
                f"Back in Stock: {product_name} ⚡",
            )
        except Exception as e:
            logger.error(f"[EMAIL] Failed back_in_stock email to {to_email}: {e}")

    async def send_abandoned_cart(
        self, to_email: str, to_name: str, cart_items: list[dict],
        cart_url: str, user_id: str | None = None,
    ) -> None:
        try:
            if not await self._check_preference(user_id, "marketing_emails"):
                logger.info(f"[EMAIL] Skipping abandoned_cart for {to_email} (preference off)")
                return

            items_html = ""
            for item in cart_items:
                items_html += (
                    f'<tr><td style="padding:10px 12px;border-bottom:1px solid #eee;">{item["name"]}</td>'
                    f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:center;">{item["quantity"]}</td>'
                    f'<td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:right;">R{item["price"]:.2f}</td></tr>'
                )

            await self._send_template(
                to_email, to_name,
                TEMPLATE_KEYS["abandoned_cart"],
                {
                    "name": to_name,
                    "items_html": items_html,
                    "cart_url": cart_url,
                },
                "abandoned_cart",
                "You Left Something Behind! 👀",
            )
        except Exception as e:
            logger.error(f"[EMAIL] Failed abandoned_cart email to {to_email}: {e}")

    async def send_new_drop_alert(
        self, to_email: str, to_name: str, set_name: str,
        set_description: str, drop_url: str, user_id: str | None = None,
    ) -> None:
        try:
            if not await self._check_preference(user_id, "new_drops"):
                logger.info(f"[EMAIL] Skipping new_drop_alert for {to_email} (preference off)")
                return
            await self._send_template(
                to_email, to_name,
                TEMPLATE_KEYS["new_drop_alert"],
                {
                    "name": to_name,
                    "set_name": set_name,
                    "set_description": set_description,
                    "drop_url": drop_url,
                },
                "new_drop_alert",
                f"New Drop: {set_name} ⚡",
            )
        except Exception as e:
            logger.error(f"[EMAIL] Failed new_drop_alert email to {to_email}: {e}")

    # ── Existing seller/marketplace emails (raw HTML, kept as-is) ─────────────

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
            logger.error(f"[EMAIL] Failed seller sale notification to {to_email}: {e}")

    async def send_seller_payout_notification(
        self, to_email: str, seller_name: str, order_number: str, payout_amount: float,
    ) -> None:
        try:
            html = SELLER_PAYOUT_NOTIFICATION_TEMPLATE.format(
                seller_name=seller_name, order_number=order_number, payout_amount=payout_amount,
            )
            await self._send(to_email, seller_name, f"Payout Created — {order_number}", html)
        except Exception as e:
            logger.error(f"[EMAIL] Failed payout notification to {to_email}: {e}")

    async def send_delivery_confirmed_to_seller(
        self, to_email: str, seller_name: str, order_number: str,
    ) -> None:
        try:
            html = DELIVERY_CONFIRMED_SELLER_TEMPLATE.format(
                seller_name=seller_name, order_number=order_number,
            )
            await self._send(to_email, seller_name, f"Delivery Confirmed — {order_number}", html)
        except Exception as e:
            logger.error(f"[EMAIL] Failed delivery confirmation to {to_email}: {e}")

    async def send_promotion_confirmation(
        self, to_email: str, seller_name: str, listing_title: str, tier: str, expires_at: str,
    ) -> None:
        try:
            html = PROMOTION_CONFIRMATION_TEMPLATE.format(
                seller_name=seller_name, listing_title=listing_title, tier=tier, expires_at=expires_at,
            )
            await self._send(to_email, seller_name, f"Promotion Activated — {listing_title}", html)
        except Exception as e:
            logger.error(f"[EMAIL] Failed promotion confirmation to {to_email}: {e}")

    async def send_test(self, to_email: str, to_name: str = "") -> None:
        await self._send(
            to_email, to_name, "Elite TCG — Email Test",
            "<h2>ZeptoMail is working!</h2><p>This is a test email from Elite TCG.</p>",
        )

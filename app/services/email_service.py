"""
Email service stub. Not wired to any routes yet.
Can be extended to send transactional emails via SMTP.
"""
import logging

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, smtp_host: str = "", smtp_port: int = 587, smtp_user: str = "", smtp_password: str = ""):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password

    async def send_order_confirmation(self, to_email: str, order_number: str, total_zar: float) -> None:
        """Placeholder — logs instead of sending."""
        logger.info(f"[EMAIL STUB] Order confirmation to {to_email} for {order_number} (R{total_zar:.2f})")

    async def send_shipping_notification(self, to_email: str, order_number: str, tracking_number: str) -> None:
        """Placeholder — logs instead of sending."""
        logger.info(f"[EMAIL STUB] Shipping notification to {to_email} for {order_number} (tracking: {tracking_number})")

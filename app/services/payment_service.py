import logging
from datetime import datetime

from app.clients.payfast_client import PayFastClient
from app.repositories.order_repo import OrderRepository
from app.repositories.product_repo import ProductRepository
from app.services.shipping_service import ShippingService
from app.services.email_service import EmailService
from app.services.telegram_service import TelegramService
from app.domain.enums import OrderStatus, PaymentStatus, ShippingMethod
from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, payfast_client: PayFastClient, order_repo: OrderRepository,
                 product_repo: ProductRepository, shipping_service: ShippingService,
                 email_service: EmailService, telegram: TelegramService | None = None):
        self.payfast = payfast_client
        self.order_repo = order_repo
        self.product_repo = product_repo
        self.shipping_service = shipping_service
        self.email_service = email_service
        self.telegram = telegram or TelegramService()

    def generate_checkout(self, order) -> dict:
        item_count = sum(item.quantity for item in order.items)
        email = order.guest_email or (order.customer.email if order.customer else "")
        name = order.guest_name or (order.customer.full_name if order.customer else "")
        parts = name.split(" ", 1)

        payment_data = self.payfast.generate_payment_data(
            order_number=order.order_number, total_zar=order.total_zar,
            item_name=f"Elite TCG -- {item_count} item(s)", email=email,
            name_first=parts[0] if parts else "", name_last=parts[1] if len(parts) > 1 else "",
        )
        return {"payment_url": self.payfast.process_url, "payment_data": payment_data}

    async def handle_itn(self, posted_data: dict, background_tasks: BackgroundTasks) -> bool:
        # 1. Verify signature
        if not self.payfast.verify_itn_signature(posted_data):
            return False

        # 2. Server validation
        if not await self.payfast.validate_itn_server(posted_data):
            return False

        # 3. Find order
        order_number = posted_data.get("m_payment_id")
        order = await self.order_repo.get_by_order_number(order_number)
        if not order:
            return False

        # 4. Verify amount
        received = float(posted_data.get("amount_gross", 0))
        if abs(received - order.total_zar) > 0.01:
            return False

        status = posted_data.get("payment_status", "")

        if status == "COMPLETE":
            await self.order_repo.update_by_id(order.id, {
                "payment_status": PaymentStatus.COMPLETE,
                "order_status": OrderStatus.PAID,
                "payfast_payment_id": posted_data.get("pf_payment_id"),
            })

            # Background: reduce stock
            background_tasks.add_task(self._reduce_stock, order)

            # Background: auto-book courier if selected
            if order.shipping_method == ShippingMethod.COURIER_GUY:
                background_tasks.add_task(self._auto_book_shipping, order.id)

            # Background: send order confirmation email
            background_tasks.add_task(self._send_order_confirmation_email, order)

            # Telegram notification (best effort)
            email = order.guest_email or (order.customer.email if order.customer else "")
            background_tasks.add_task(
                self.telegram.notify_order_paid,
                order.order_number, order.total_zar, email,
            )

            return True

        elif status == "CANCELLED":
            await self.order_repo.update_by_id(order.id, {
                "payment_status": PaymentStatus.CANCELLED,
                "order_status": OrderStatus.CANCELLED,
            })
            return True

        elif status == "FAILED":
            await self.order_repo.update_by_id(order.id, {
                "payment_status": PaymentStatus.FAILED,
            })

            # Background: send payment failed email
            background_tasks.add_task(self._send_payment_failed_email, order)

            return True

        return False

    async def _reduce_stock(self, order) -> None:
        for item in order.items:
            await self.product_repo.reduce_stock(item.product_id, item.quantity)

    async def _auto_book_shipping(self, order_id: str) -> None:
        try:
            await self.shipping_service.book_shipment(order_id)
        except Exception as e:
            logger.warning(f"Auto-ship failed for {order_id}: {e}")

    async def _send_order_confirmation_email(self, order) -> None:
        try:
            to_email = order.guest_email or (order.customer.email if order.customer else "")
            to_name = order.guest_name or (order.customer.name if order.customer else "Customer")
            if not to_email:
                return

            order_items = [
                {
                    "name": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price_zar,
                    "line_total": item.line_total_zar,
                }
                for item in order.items
            ]

            shipping_address = ", ".join(filter(None, [
                order.shipping_address_line1,
                order.shipping_address_line2,
                order.shipping_city,
                order.shipping_province,
                order.shipping_postal_code,
            ]))

            await self.email_service.send_order_confirmation(
                to_email=to_email,
                to_name=to_name,
                order_number=order.order_number,
                order_items=order_items,
                subtotal=order.subtotal_zar,
                shipping_cost=order.shipping_cost_zar,
                total=order.total_zar,
                shipping_address=shipping_address or "Collection",
                order_date=datetime.now().strftime("%d %B %Y"),
            )
        except Exception as e:
            logger.error(f"[EMAIL] Failed to send order confirmation for {order.order_number}: {e}")

    async def _send_payment_failed_email(self, order) -> None:
        try:
            to_email = order.guest_email or (order.customer.email if order.customer else "")
            to_name = order.guest_name or (order.customer.name if order.customer else "Customer")
            if not to_email:
                return

            retry_url = f"https://www.elitetcg.co.za/cart"
            await self.email_service.send_payment_failed(to_email, to_name, order.order_number, retry_url)
        except Exception as e:
            logger.error(f"[EMAIL] Failed to send payment_failed for {order.order_number}: {e}")

import logging

from app.clients.courier_guy_client import CourierGuyClient
from app.repositories.order_repo import OrderRepository
from app.services.pricing_service import PricingService
from app.services.email_service import EmailService
from app.domain.enums import OrderStatus

logger = logging.getLogger(__name__)


class ShippingService:
    def __init__(self, courier_client: CourierGuyClient, order_repo: OrderRepository,
                 pricing_service: PricingService, email_service: EmailService | None = None):
        self.courier_client = courier_client
        self.order_repo = order_repo
        self.pricing_service = pricing_service
        self.email_service = email_service

    async def get_quote(self, address: str, city: str, province: str, postal_code: str, total_weight_grams: int) -> dict:
        weight_kg = max(total_weight_grams / 1000, 0.5)
        quote = await self.courier_client.get_quote(address, city, province, postal_code, weight_kg)
        if not quote:
            raise ValueError("Could not get shipping quote. Please check the address.")
        pricing = self.pricing_service.calculate_shipping_customer_price(quote["rate_zar"])
        return {**pricing, "estimated_days": quote["estimated_days"], "service_name": quote["service_name"]}

    async def book_shipment(self, order_id: str) -> dict:
        order = await self.order_repo.get_by_id_with_items(order_id)
        if not order:
            raise ValueError("Order not found")
        if order.order_status not in (OrderStatus.PAID, OrderStatus.CONFIRMED):
            raise ValueError(f"Cannot ship order in status: {order.order_status}")

        total_weight_kg = sum((item.quantity * 100) / 1000 for item in order.items)
        customer_name = order.guest_name or (order.customer.full_name if order.customer else "Customer")
        customer_phone = order.guest_phone or (order.customer.phone if order.customer else "")
        customer_email = order.guest_email or (order.customer.email if order.customer else "")

        result = await self.courier_client.book_shipment(
            order_number=order.order_number,
            destination_address=order.shipping_address_line1 or "",
            destination_city=order.shipping_city or "",
            destination_province=order.shipping_province or "",
            destination_postal_code=order.shipping_postal_code or "",
            destination_contact_name=customer_name,
            destination_contact_phone=customer_phone,
            destination_contact_email=customer_email,
            total_weight_kg=total_weight_kg,
        )
        if not result:
            raise ValueError("Failed to book shipment with Courier Guy")

        await self.order_repo.update_by_id(order_id, {
            "courier_tracking_number": result["tracking_number"],
            "courier_booking_reference": result["booking_reference"],
            "order_status": OrderStatus.SHIPPED,
        })

        # Send shipping notification email
        if self.email_service and customer_email:
            try:
                tracking_url = f"https://www.thecourierguy.co.za/tracking?waybill={result['tracking_number']}"
                await self.email_service.send_shipping_notification(
                    to_email=customer_email,
                    to_name=customer_name,
                    order_number=order.order_number,
                    tracking_number=result["tracking_number"],
                    courier="The Courier Guy",
                    tracking_url=tracking_url,
                )
            except Exception as e:
                logger.error(f"[EMAIL] Failed to send shipping notification for {order.order_number}: {e}")

        return result

    async def handle_webhook(self, tracking_number: str, status: str) -> None:
        status_map = {
            "collected": OrderStatus.SHIPPED,
            "in_transit": OrderStatus.IN_TRANSIT,
            "out_for_delivery": OrderStatus.OUT_FOR_DELIVERY,
            "delivered": OrderStatus.DELIVERED,
        }
        new_status = status_map.get(status.lower())
        if not new_status:
            return
        order = await self.order_repo.get_by_tracking_number(tracking_number)
        if order:
            await self.order_repo.update_by_id(order.id, {"order_status": new_status})

            # Send delivery confirmation email when delivered
            if new_status == OrderStatus.DELIVERED and self.email_service:
                try:
                    to_email = order.guest_email or (order.customer.email if order.customer else "")
                    to_name = order.guest_name or (order.customer.name if order.customer else "Customer")
                    if to_email:
                        await self.email_service.send_delivery_confirmation(to_email, to_name, order.order_number)
                except Exception as e:
                    logger.error(f"[EMAIL] Failed to send delivery confirmation for {order.order_number}: {e}")

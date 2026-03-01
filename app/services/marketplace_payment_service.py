"""Marketplace PayFast payment service — ported from EliteTCG_API/routes/payfast.js."""
import logging
import uuid
from datetime import datetime, timezone

from app.clients.payfast_client import PayFastClient
from app.config import get_settings
from app.repositories.marketplace_repo import MarketplaceRepository
from app.services.commission_service import calculate_commission
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class MarketplacePaymentService:
    def __init__(
        self,
        payfast: PayFastClient,
        repo: MarketplaceRepository,
        email: EmailService,
    ):
        self.payfast = payfast
        self.repo = repo
        self.email = email
        self.settings = get_settings()

    async def create_payment(
        self, listing_id: str, quantity: int, buyer_email: str, buyer_name: str,
        buyer_phone: str | None = None, shipping_address: dict | None = None,
        buyer_id: str | None = None,
    ) -> dict:
        listing = await self.repo.get_active_listing(listing_id)
        if not listing:
            raise ValueError("Listing not found or not active")

        if listing.quantity < quantity:
            raise ValueError(f"Only {listing.quantity} available")

        # Get seller profile for payfast_email
        seller = await self.repo.get_seller_profile_by_customer_id(listing.seller_id)
        if not seller:
            raise ValueError("Seller profile not found")

        # Reserve listing
        reserved = await self.repo.reserve_listing(listing_id, buyer_id, quantity)
        if not reserved:
            raise ValueError("Could not reserve listing — it may already be reserved")

        # Calculate commission
        subtotal = listing.price * quantity
        commission = calculate_commission(subtotal)
        platform_fee = commission["amount"]
        seller_amount = commission["seller_receives"]

        # Generate order number
        order_number = f"MKT-{uuid.uuid4().hex[:8].upper()}"

        import json
        shipping_json = json.dumps(shipping_address) if shipping_address else None

        order = await self.repo.create_marketplace_order(
            order_number=order_number,
            listing_id=listing_id,
            seller_id=listing.seller_id,
            buyer_id=buyer_id,
            quantity=quantity,
            unit_price=listing.price,
            subtotal=subtotal,
            platform_fee=platform_fee,
            platform_fee_percentage=commission["rate"],
            seller_amount=seller_amount,
            total_amount=subtotal,
            buyer_email=buyer_email,
            buyer_name=buyer_name,
            buyer_phone=buyer_phone,
            shipping_address=shipping_json,
            listing_title=listing.title,
        )

        # Build PayFast payment data
        name_parts = buyer_name.split(" ", 1)
        name_first = name_parts[0]
        name_last = name_parts[1] if len(name_parts) > 1 else ""

        payment_data = self.payfast.generate_marketplace_payment_data(
            order_id=order.id,
            order_number=order_number,
            total_zar=subtotal,
            item_name=listing.title,
            email=buyer_email,
            name_first=name_first,
            name_last=name_last,
            notify_url=self.settings.payfast_marketplace_notify_url,
            return_url=f"{self.settings.payfast_marketplace_return_url}?order={order.id}",
            cancel_url=self.settings.payfast_marketplace_cancel_url,
            custom_str1=order_number,
            custom_str2=listing_id,
            custom_str3=seller.payfast_email or "",
            custom_str4=f"{seller_amount:.2f}",
            custom_int1=quantity,
        )

        return {
            "order": {
                "id": order.id,
                "order_number": order_number,
                "total_amount": subtotal,
            },
            "payment_url": self.payfast.process_url,
            "payment_data": payment_data,
        }

    async def handle_marketplace_itn(self, posted: dict) -> bool:
        logger.info(f"[MARKETPLACE ITN] Received: m_payment_id={posted.get('m_payment_id')}")

        if not self.payfast.verify_itn_signature(posted):
            logger.warning("[MARKETPLACE ITN] Invalid signature")
            return False

        order_id = posted.get("m_payment_id", "")
        payment_status = posted.get("payment_status", "")

        order = await self.repo.get_marketplace_order(order_id)
        if not order:
            logger.error(f"[MARKETPLACE ITN] Order not found: {order_id}")
            return False

        if payment_status == "COMPLETE":
            # Verify amount
            expected = f"{order.total_amount:.2f}"
            received = posted.get("amount_gross", "0.00")
            if expected != received:
                logger.warning(f"[MARKETPLACE ITN] Amount mismatch: expected={expected} received={received}")
                return False

            # Update order
            now = datetime.now(timezone.utc)
            await self.repo.update_marketplace_order(
                order_id,
                status="paid",
                payment_status="completed",
                payfast_payment_id=posted.get("pf_payment_id"),
                paid_at=now,
            )

            # Update listing quantity
            await self.repo.update_listing_after_sale(order.listing_id, order.quantity)

            # Create seller payout
            await self.repo.create_seller_payout(
                seller_id=order.seller_id,
                order_id=order.id,
                amount=order.seller_amount,
            )

            # Send emails (best effort)
            try:
                await self.email.send_order_confirmation(
                    order.buyer_email, order.order_number, order.total_amount, order.buyer_name,
                )
            except Exception as e:
                logger.error(f"[MARKETPLACE ITN] Buyer email failed: {e}")

            try:
                seller = await self.repo.get_seller_profile_by_customer_id(order.seller_id)
                if seller:
                    seller_email = seller.contact_email or seller.payfast_email
                    if seller_email:
                        await self.email.send_seller_sale_notification(
                            seller_email, seller.display_name or "Seller",
                            order.order_number, order.listing_title or "",
                            order.quantity, order.seller_amount,
                        )
                        await self.email.send_seller_payout_notification(
                            seller_email, seller.display_name or "Seller",
                            order.order_number, order.seller_amount,
                        )
            except Exception as e:
                logger.error(f"[MARKETPLACE ITN] Seller email failed: {e}")

            logger.info(f"[MARKETPLACE ITN] Payment complete: {order_id}")
            return True

        elif payment_status == "CANCELLED":
            await self.repo.update_marketplace_order(
                order_id, status="cancelled", payment_status="cancelled",
            )
            await self.repo.release_reservation(order.listing_id)
            logger.info(f"[MARKETPLACE ITN] Payment cancelled: {order_id}")
            return True

        return True

    async def get_order_status(self, order_id: str, buyer_id: str | None = None) -> dict | None:
        order = await self.repo.get_marketplace_order(order_id)
        if not order:
            return None

        # Allow access if buyer owns it, or if order is recent (24 hours)
        if buyer_id and order.buyer_id and order.buyer_id != buyer_id:
            created = order.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
            if age_hours > 24:
                return None

        return {
            "id": order.id,
            "order_number": order.order_number,
            "total_amount": order.total_amount,
            "status": order.status,
            "payment_status": order.payment_status,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "listing_title": order.listing_title,
        }

    async def confirm_delivery(self, order_id: str, buyer_id: str) -> dict:
        order = await self.repo.get_marketplace_order(order_id)
        if not order:
            raise ValueError("Order not found")

        if order.buyer_id != buyer_id:
            raise PermissionError("Not authorized")

        if order.status not in ("paid", "shipped"):
            raise ValueError(f"Cannot confirm delivery for order in status: {order.status}")

        now = datetime.now(timezone.utc)
        await self.repo.update_marketplace_order(
            order_id, status="delivered", delivered_at=now,
        )

        # Notify seller
        try:
            seller = await self.repo.get_seller_profile_by_customer_id(order.seller_id)
            if seller:
                seller_email = seller.contact_email or seller.payfast_email
                if seller_email:
                    await self.email.send_delivery_confirmed_to_seller(
                        seller_email, seller.display_name or "Seller", order.order_number,
                    )
        except Exception as e:
            logger.error(f"[MARKETPLACE] Delivery notification failed: {e}")

        return {"status": "delivered", "order_number": order.order_number}

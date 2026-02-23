"""
The Courier Guy API.
Docs: https://developer.thecourierguy.co.za/

Flow:
1. Get quote -> customer sees live shipping price at checkout
2. Book shipment -> Courier Guy collects from YOUR address, delivers to customer
3. Webhook -> status updates (collected, in_transit, out_for_delivery, delivered)
4. Customer gets WhatsApp tracking from Courier Guy automatically
"""
import httpx
import hmac
import hashlib
from app.config import get_settings
from app.domain.constants import (
    MIN_PARCEL_WEIGHT_KG, DEFAULT_PARCEL_LENGTH,
    DEFAULT_PARCEL_WIDTH, DEFAULT_PARCEL_HEIGHT,
)


class CourierGuyClient:
    BASE_URL = "https://api.thecourierguy.co.za/v2"

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.courier_guy_api_key
        self.account_number = settings.courier_guy_account_number
        self.webhook_secret = settings.courier_guy_webhook_secret
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        self.seller_address = {
            "street_address": settings.seller_address_line1,
            "city": settings.seller_city,
            "province": settings.seller_province,
            "postal_code": settings.seller_postal_code,
            "contact_name": "Pokemon Cards SA",
            "contact_phone": settings.seller_phone,
            "type": "business",
        }

    async def get_quote(
        self, destination_address: str, destination_city: str,
        destination_province: str, destination_postal_code: str,
        total_weight_kg: float, parcels: int = 1,
    ) -> dict | None:
        """Get cheapest shipping rate."""
        payload = {
            "collection_address": self.seller_address,
            "delivery_address": {
                "street_address": destination_address, "city": destination_city,
                "province": destination_province, "postal_code": destination_postal_code,
                "type": "residential",
            },
            "parcels": [{
                "weight": max(total_weight_kg, MIN_PARCEL_WEIGHT_KG),
                "length": DEFAULT_PARCEL_LENGTH, "width": DEFAULT_PARCEL_WIDTH,
                "height": DEFAULT_PARCEL_HEIGHT,
            } for _ in range(parcels)],
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.BASE_URL}/rates", json=payload, headers=self.headers, timeout=15.0)
            if resp.status_code == 200:
                rates = resp.json().get("rates", [])
                if rates:
                    cheapest = min(rates, key=lambda r: r.get("rate", float("inf")))
                    return {
                        "service_type": cheapest.get("service_type", "standard"),
                        "rate_zar": float(cheapest.get("rate", 0)),
                        "estimated_days": int(cheapest.get("estimated_delivery_days", 3)),
                        "service_name": cheapest.get("service_name", "Standard"),
                    }
        return None

    async def book_shipment(
        self, order_number: str, destination_address: str, destination_city: str,
        destination_province: str, destination_postal_code: str,
        destination_contact_name: str, destination_contact_phone: str,
        destination_contact_email: str, total_weight_kg: float,
        description: str = "Pokemon Trading Cards",
    ) -> dict | None:
        """Book collection from seller + delivery to customer. Returns tracking info."""
        payload = {
            "account_number": self.account_number,
            "collection_address": self.seller_address,
            "delivery_address": {
                "street_address": destination_address, "city": destination_city,
                "province": destination_province, "postal_code": destination_postal_code,
                "contact_name": destination_contact_name, "contact_phone": destination_contact_phone,
                "contact_email": destination_contact_email, "type": "residential",
            },
            "parcels": [{
                "weight": max(total_weight_kg, MIN_PARCEL_WEIGHT_KG),
                "length": DEFAULT_PARCEL_LENGTH, "width": DEFAULT_PARCEL_WIDTH,
                "height": DEFAULT_PARCEL_HEIGHT, "description": description,
            }],
            "special_instructions": f"Order {order_number} -- Handle with care",
            "reference": order_number,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.BASE_URL}/shipments", json=payload, headers=self.headers, timeout=15.0)
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "tracking_number": data.get("tracking_number"),
                    "booking_reference": data.get("reference"),
                    "collection_date": data.get("estimated_collection_date"),
                    "tracking_url": f"https://tracking.thecourierguy.co.za/{data.get('tracking_number', '')}",
                }
        return None

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        if not self.webhook_secret:
            return True
        expected = hmac.new(self.webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

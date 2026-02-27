from app.domain.constants import SHIPPING_HANDLING_FEE_ZAR


class PricingService:
    """Simplified pricing service — shipping cost calculations only."""

    def calculate_shipping_customer_price(self, courier_quote_zar: float) -> dict:
        customer_price = courier_quote_zar + SHIPPING_HANDLING_FEE_ZAR
        return {
            "courier_cost_zar": round(courier_quote_zar, 2),
            "customer_cost_zar": round(customer_price, 2),
            "handling_fee_zar": SHIPPING_HANDLING_FEE_ZAR,
        }

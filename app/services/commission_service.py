import logging

logger = logging.getLogger(__name__)


def calculate_commission(price_zar: float) -> dict:
    """Calculate tiered marketplace commission on a ZAR price.

    Tiers (per-listing):
        < R10        = 0%
        R10 – R50    = 8%
        R51 – R100   = 7.5%
        R101 – R1000 = 6%
        R1001 – R5000 = 5%
        > R5000      = 4%

    Returns dict with rate, amount, seller_receives, and description.
    """
    if price_zar <= 0:
        return {
            "rate": 0.0,
            "amount": 0.0,
            "seller_receives": 0.0,
            "description": "No commission on zero or negative price",
        }

    if price_zar < 10:
        rate = 0.0
        description = "0% (under R10)"
    elif price_zar <= 50:
        rate = 0.08
        description = "8% (R10–R50)"
    elif price_zar <= 100:
        rate = 0.075
        description = "7.5% (R51–R100)"
    elif price_zar <= 1000:
        rate = 0.06
        description = "6% (R101–R1,000)"
    elif price_zar <= 5000:
        rate = 0.05
        description = "5% (R1,001–R5,000)"
    else:
        rate = 0.04
        description = "4% (R5,000+)"

    amount = round(price_zar * rate, 2)
    seller_receives = round(price_zar - amount, 2)

    return {
        "rate": rate,
        "amount": amount,
        "seller_receives": seller_receives,
        "description": description,
    }

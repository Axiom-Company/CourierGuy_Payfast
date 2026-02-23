from app.domain.enums import CardCondition

# Multiplier applied to market price based on card condition
CONDITION_MULTIPLIERS: dict[CardCondition, float] = {
    CardCondition.MINT: 1.00,
    CardCondition.NEAR_MINT: 0.95,
    CardCondition.LIGHTLY_PLAYED: 0.85,
    CardCondition.MODERATELY_PLAYED: 0.70,
    CardCondition.HEAVILY_PLAYED: 0.50,
    CardCondition.DAMAGED: 0.30,
}

# Shipping
SHIPPING_HANDLING_FEE_ZAR = 25.00   # Added on top of courier quote
MIN_PARCEL_WEIGHT_KG = 0.5          # Courier Guy minimum
DEFAULT_CARD_WEIGHT_GRAMS = 100     # Single card in toploader + mailer
DEFAULT_SEALED_WEIGHT_GRAMS = 500   # Booster box etc.

# Parcel dimensions (cm) — standard card shipping box
DEFAULT_PARCEL_LENGTH = 30
DEFAULT_PARCEL_WIDTH = 20
DEFAULT_PARCEL_HEIGHT = 10

# Order number format
ORDER_NUMBER_PREFIX = "PKM"

# Pagination
DEFAULT_PAGE_SIZE = 24
MAX_PAGE_SIZE = 100

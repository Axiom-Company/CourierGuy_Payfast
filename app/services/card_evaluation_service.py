import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.pokemon_tcg_client import PokemonTCGClient
from app.services import exchange_rate_service, commission_service
from app.domain.enums import CardCondition

logger = logging.getLogger(__name__)

# Condition multipliers applied to market price.
# Supports both full enum values (Mint, NM, LP, MP, HP, Damaged)
# and the short code 'D' that the frontend sends for Damaged.
CONDITION_MULTIPLIERS: dict[str, float] = {
    CardCondition.MINT.value: 1.00,       # "Mint"
    CardCondition.NEAR_MINT.value: 0.95,  # "NM"
    CardCondition.LIGHTLY_PLAYED.value: 0.85,  # "LP"
    CardCondition.MODERATELY_PLAYED.value: 0.70,  # "MP"
    CardCondition.HEAVILY_PLAYED.value: 0.50,  # "HP"
    CardCondition.DAMAGED.value: 0.30,    # "Damaged"
    "D": 0.30,                            # Short code alias for Damaged
}

_tcg_client = PokemonTCGClient()


async def evaluate_card(
    set_id: str,
    number: str,
    condition: str,
    db: AsyncSession,
) -> dict:
    """Full card evaluation: lookup + currency conversion + condition adjustment + commission.

    Args:
        set_id: Pokemon TCG set ID (e.g. 'sv7').
        number: Card number within the set (e.g. '25').
        condition: Card condition string matching CardCondition enum values.
        db: Async database session for exchange rate caching.

    Returns:
        Dict with card data, pricing breakdown, and commission info.
    """
    card = await _tcg_client.lookup_card(set_id, number)
    if card is None:
        return {"error": f"Card {set_id}-{number} not found"}

    market_price_usd = card.get("market_price_usd")
    if market_price_usd is None:
        return {
            "card": card,
            "error": "No market price available for this card",
            "condition": condition,
        }

    rate = await exchange_rate_service.get_current_rate(db)

    market_price_zar = round(market_price_usd * rate, 2)

    multiplier = CONDITION_MULTIPLIERS.get(condition, 0.95)
    suggested_price_zar = round(market_price_zar * multiplier, 2)

    commission = commission_service.calculate_commission(suggested_price_zar)

    return {
        "card": card,
        "condition": condition,
        "condition_multiplier": multiplier,
        "exchange_rate": round(rate, 4),
        "market_price_usd": round(market_price_usd, 2),
        "market_price_zar": market_price_zar,
        "suggested_price_zar": suggested_price_zar,
        "commission": commission,
        "seller_receives_zar": commission["seller_receives"],
    }

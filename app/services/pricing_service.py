from app.clients.pokemon_tcg_client import PokemonTCGClient
from app.repositories.exchange_rate_repo import ExchangeRateRepository
from app.domain.enums import CardCondition
from app.domain.constants import CONDITION_MULTIPLIERS, SHIPPING_HANDLING_FEE_ZAR
from app.config import get_settings


class PricingService:
    def __init__(self, pokemon_client: PokemonTCGClient, exchange_rate_repo: ExchangeRateRepository):
        self.pokemon_client = pokemon_client
        self.exchange_rate_repo = exchange_rate_repo

    async def get_exchange_rate(self) -> float:
        rate = await self.exchange_rate_repo.get_latest("USD", "ZAR")
        return rate.rate if rate else get_settings().usd_to_zar_default

    async def get_card_pricing(
        self, tcg_id: str, condition: CardCondition,
        margin_percent: float = 30.0, cost_price_zar: float | None = None,
    ) -> dict:
        """Full pricing breakdown for a single card."""
        card_data = await self.pokemon_client.get_card(tcg_id)
        if not card_data:
            raise ValueError(f"Card not found: {tcg_id}")

        market_usd = self.pokemon_client.extract_market_price(card_data)
        exchange_rate = await self.get_exchange_rate()
        multiplier = CONDITION_MULTIPLIERS.get(condition, 0.95)

        market_zar = (market_usd or 0) * exchange_rate
        adjusted_zar = market_zar * multiplier
        sell_price_zar = adjusted_zar * (1 + margin_percent / 100)

        return {
            "card_data": card_data,
            "market_price_usd": market_usd,
            "market_price_zar": round(market_zar, 2),
            "condition_multiplier": multiplier,
            "adjusted_market_zar": round(adjusted_zar, 2),
            "sell_price_zar": round(sell_price_zar, 2),
            "profit_zar": round(sell_price_zar - (cost_price_zar or 0), 2),
            "exchange_rate": exchange_rate,
        }

    def calculate_sealed_margin(self, cost: float, sell: float) -> float:
        if cost <= 0:
            return 0.0
        return round(((sell - cost) / cost) * 100, 1)

    def calculate_shipping_customer_price(self, courier_quote_zar: float) -> dict:
        customer_price = courier_quote_zar + SHIPPING_HANDLING_FEE_ZAR
        return {
            "courier_cost_zar": round(courier_quote_zar, 2),
            "customer_cost_zar": round(customer_price, 2),
            "handling_fee_zar": SHIPPING_HANDLING_FEE_ZAR,
        }

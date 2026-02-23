from app.repositories.product_repo import ProductRepository
from app.clients.pokemon_tcg_client import PokemonTCGClient
from app.services.pricing_service import PricingService
from app.domain.models.product import Product
from app.domain.enums import ProductType, CardCondition
from app.domain.constants import CONDITION_MULTIPLIERS, DEFAULT_SEALED_WEIGHT_GRAMS
from app.domain.schemas.product import SealedProductCreate, SingleCardCreate, PriceCheckResponse


class ProductService:
    def __init__(self, repo: ProductRepository, pokemon_client: PokemonTCGClient, pricing: PricingService):
        self.repo = repo
        self.pokemon_client = pokemon_client
        self.pricing = pricing

    async def browse_query(
        self, q: str | None = None, product_type=None, sealed_category: str | None = None,
        set_name: str | None = None, rarity: str | None = None, condition=None,
        min_price: float | None = None, max_price: float | None = None, sort: str = "newest",
    ):
        """Delegates to ProductRepository.browse() and returns the query for pagination."""
        return await self.repo.browse(
            q=q, product_type=product_type, sealed_category=sealed_category,
            set_name=set_name, rarity=rarity, condition=condition,
            min_price=min_price, max_price=max_price, sort=sort,
        )

    async def get_by_id(self, product_id: str) -> Product | None:
        return await self.repo.get_by_id(product_id)

    async def get_featured(self, limit: int = 8) -> list[Product]:
        return await self.repo.get_featured(limit)

    async def get_sets(self) -> list[dict]:
        return await self.pokemon_client.get_sets()

    async def create_sealed(self, data: SealedProductCreate, seller_id: str) -> Product:
        """Create a sealed product listing."""
        margin = 0.0
        if data.cost_price_zar and data.cost_price_zar > 0:
            margin = self.pricing.calculate_sealed_margin(data.cost_price_zar, data.sell_price_zar)

        product = Product(
            product_type=ProductType.SEALED,
            name=data.name,
            description=data.description,
            sealed_category=data.sealed_category,
            set_name=data.set_name,
            cost_price_zar=data.cost_price_zar,
            sell_price_zar=data.sell_price_zar,
            margin_percent=margin,
            quantity=data.quantity,
            weight_grams=data.weight_grams,
            listed_by=seller_id,
        )
        return await self.repo.create(product)

    async def create_single(self, data: SingleCardCreate, seller_id: str) -> Product:
        """Create a single card listing. Fetches all data from pokemontcg.io."""
        pricing = await self.pricing.get_card_pricing(
            tcg_id=data.tcg_id,
            condition=data.condition,
            margin_percent=data.margin_percent,
            cost_price_zar=data.cost_price_zar,
        )
        card_data = pricing["card_data"]
        multiplier = CONDITION_MULTIPLIERS.get(data.condition, 0.95)

        product = Product(
            product_type=ProductType.SINGLE,
            name=card_data.get("name", "Unknown Card"),
            tcg_id=data.tcg_id,
            card_number=card_data.get("number"),
            set_id=card_data.get("set", {}).get("id"),
            set_name=card_data.get("set", {}).get("name"),
            rarity=card_data.get("rarity"),
            card_type=(card_data.get("types") or [None])[0],
            hp=card_data.get("hp"),
            artist=card_data.get("artist"),
            condition=data.condition,
            condition_multiplier=multiplier,
            tcg_image_small=card_data.get("images", {}).get("small"),
            tcg_image_large=card_data.get("images", {}).get("large"),
            market_price_usd=pricing["market_price_usd"],
            market_price_zar=pricing["market_price_zar"],
            cost_price_zar=data.cost_price_zar,
            margin_percent=data.margin_percent,
            sell_price_zar=pricing["sell_price_zar"],
            quantity=data.quantity,
            weight_grams=100,
            listed_by=seller_id,
        )
        return await self.repo.create(product)

    async def update(self, product_id: str, values: dict) -> Product | None:
        """Partial update for any product."""
        return await self.repo.update_by_id(product_id, values)

    async def delist(self, product_id: str) -> None:
        """Soft-delete a product by setting status to delisted."""
        await self.repo.update_by_id(product_id, {"status": "delisted"})

    async def inventory_query(self, seller_id: str, q: str | None = None, status: str | None = None):
        """Returns the query for seller inventory pagination."""
        return await self.repo.get_by_seller(seller_id, q, status)

    async def get_inventory_stats(self, seller_id: str) -> dict:
        return await self.repo.get_inventory_stats(seller_id)

    async def search_tcg_cards(self, q: str) -> dict:
        return await self.pokemon_client.search_cards(q)

    async def get_price_check(self, tcg_id: str, condition: str, margin: float, cost: float | None) -> PriceCheckResponse:
        """Full pricing preview before listing a card."""
        cond = CardCondition(condition)
        pricing = await self.pricing.get_card_pricing(tcg_id, cond, margin, cost)
        card_data = pricing["card_data"]

        return PriceCheckResponse(
            tcg_id=tcg_id,
            card_name=card_data.get("name", "Unknown"),
            set_name=card_data.get("set", {}).get("name", "Unknown"),
            rarity=card_data.get("rarity"),
            tcg_image_small=card_data.get("images", {}).get("small"),
            tcg_image_large=card_data.get("images", {}).get("large"),
            market_price_usd=pricing["market_price_usd"],
            exchange_rate=pricing["exchange_rate"],
            market_price_zar=pricing["market_price_zar"],
            condition=condition,
            condition_multiplier=pricing["condition_multiplier"],
            adjusted_market_zar=pricing["adjusted_market_zar"],
            margin_percent=margin,
            sell_price_zar=pricing["sell_price_zar"],
            cost_price_zar=cost,
            profit_zar=pricing["profit_zar"],
        )

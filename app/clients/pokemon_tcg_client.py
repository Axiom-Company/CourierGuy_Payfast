"""
pokemontcg.io v2 API wrapper.
Docs: https://docs.pokemontcg.io/
Rate limit: 20,000/day with API key, 1,000 without.
"""
import logging
import httpx
from cachetools import TTLCache
from app.config import get_settings

logger = logging.getLogger(__name__)


class PokemonTCGClient:
    BASE_URL = "https://api.pokemontcg.io/v2"

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.pokemon_tcg_api_key
        self.headers = {"X-Api-Key": self.api_key} if self.api_key else {}
        self._card_cache = TTLCache(maxsize=500, ttl=900)    # 15 min
        self._set_cache = TTLCache(maxsize=100, ttl=3600)    # 1 hour

    def _parse_market_price(self, card_data: dict) -> float | None:
        """Extract best market price from TCGPlayer data.

        Priority: holofoil > reverseHolofoil > normal > 1stEditionHolofoil.
        For each variant, tries market > mid > low.
        Returns USD or None.
        """
        prices = card_data.get("tcgplayer", {}).get("prices", {})
        for variant in ["holofoil", "reverseHolofoil", "normal", "1stEditionHolofoil"]:
            for key in ["market", "mid", "low"]:
                price = prices.get(variant, {}).get(key)
                if price and price > 0:
                    return float(price)
        return None

    def _parse_card(self, card_data: dict) -> dict:
        """Extract a normalized flat card dict from the raw API response.

        Returns flat keys (set_name, set_id, image) so the frontend can
        consume them directly without nested object traversal.
        """
        images = card_data.get("images", {})
        tcgplayer = card_data.get("tcgplayer", {})
        card_set = card_data.get("set", {})
        market_price_usd = self._parse_market_price(card_data)

        return {
            "id": card_data.get("id", ""),
            "name": card_data.get("name", ""),
            "supertype": card_data.get("supertype", ""),
            "hp": card_data.get("hp"),
            "types": card_data.get("types", []),
            "set_id": card_set.get("id", ""),
            "set_name": card_set.get("name", ""),
            "number": card_data.get("number", ""),
            "rarity": card_data.get("rarity", ""),
            "image": images.get("small", ""),
            "image_large": images.get("large", ""),
            "tcgplayer_url": tcgplayer.get("url", ""),
            "market_price_usd": market_price_usd,
        }

    async def search_cards(
        self, query: str, set_id: str | None = None,
        page: int = 1, page_size: int = 20,
    ) -> dict:
        """Search cards by name, optionally filtered by set.

        Returns { data: [...], totalCount, page, pageSize }.
        """
        q_parts = [f"name:{query}*"]
        if set_id:
            q_parts.append(f"set.id:{set_id}")
        q_string = " ".join(q_parts)

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.BASE_URL}/cards",
                    params={
                        "q": q_string,
                        "page": page,
                        "pageSize": page_size,
                        "orderBy": "-set.releaseDate",
                    },
                    headers=self.headers,
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    raw = resp.json()
                    return {
                        "data": [self._parse_card(c) for c in raw.get("data", [])],
                        "totalCount": raw.get("totalCount", 0),
                        "page": raw.get("page", page),
                        "pageSize": raw.get("pageSize", page_size),
                    }
            except httpx.HTTPError as exc:
                logger.error("Pokemon TCG search failed: %s", exc)

        return {"data": [], "totalCount": 0, "page": page, "pageSize": page_size}

    async def lookup_card(self, set_id: str, number: str) -> dict | None:
        """Lookup a specific card by set ID and card number (e.g. 'sv7', '25').

        Constructs the pokemontcg.io ID as '{set_id}-{number}'.
        Returns parsed card dict or None.
        """
        tcg_id = f"{set_id}-{number}"
        if tcg_id in self._card_cache:
            return self._card_cache[tcg_id]

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.BASE_URL}/cards/{tcg_id}",
                    headers=self.headers,
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    data = resp.json()["data"]
                    parsed = self._parse_card(data)
                    self._card_cache[tcg_id] = parsed
                    return parsed
            except httpx.HTTPError as exc:
                logger.error("Pokemon TCG lookup failed for %s: %s", tcg_id, exc)

        return None

    async def get_sets(self) -> list[dict]:
        """Get all Pokemon TCG sets, newest first."""
        if "all_sets" in self._set_cache:
            return self._set_cache["all_sets"]

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.BASE_URL}/sets",
                    params={"orderBy": "-releaseDate"},
                    headers=self.headers,
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    sets = resp.json()["data"]
                    self._set_cache["all_sets"] = sets
                    return sets
            except httpx.HTTPError as exc:
                logger.error("Pokemon TCG get_sets failed: %s", exc)

        return []

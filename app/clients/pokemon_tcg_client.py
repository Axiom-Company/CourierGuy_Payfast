"""
pokemontcg.io v2 API wrapper.
Docs: https://docs.pokemontcg.io/
Rate limit: 20,000/day with API key, 1,000 without.
"""
import httpx
from cachetools import TTLCache
from app.config import get_settings


class PokemonTCGClient:
    BASE_URL = "https://api.pokemontcg.io/v2"

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.pokemon_tcg_api_key
        self.headers = {"X-Api-Key": self.api_key} if self.api_key else {}
        self._card_cache = TTLCache(maxsize=500, ttl=900)   # 15 min
        self._set_cache = TTLCache(maxsize=100, ttl=3600)    # 1 hour

    async def get_card(self, tcg_id: str) -> dict | None:
        """Fetch card by pokemontcg.io ID (e.g. 'sv7-25')."""
        if tcg_id in self._card_cache:
            return self._card_cache[tcg_id]

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/cards/{tcg_id}", headers=self.headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()["data"]
                self._card_cache[tcg_id] = data
                return data
        return None

    async def search_cards(self, query: str, page: int = 1, page_size: int = 20) -> dict:
        """Search cards by name. Returns { data, totalCount, page, pageSize }."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/cards",
                params={"q": f"name:{query}*", "page": page, "pageSize": page_size, "orderBy": "-set.releaseDate"},
                headers=self.headers, timeout=10.0,
            )
            if resp.status_code == 200:
                return resp.json()
        return {"data": [], "totalCount": 0}

    async def get_sets(self) -> list[dict]:
        """Get all Pokemon TCG sets, newest first."""
        if "all_sets" in self._set_cache:
            return self._set_cache["all_sets"]

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/sets", params={"orderBy": "-releaseDate"}, headers=self.headers, timeout=10.0)
            if resp.status_code == 200:
                sets = resp.json()["data"]
                self._set_cache["all_sets"] = sets
                return sets
        return []

    def extract_market_price(self, card_data: dict) -> float | None:
        """Extract best market price from TCGPlayer data. Returns USD or None."""
        prices = card_data.get("tcgplayer", {}).get("prices", {})
        for variant in ["holofoil", "normal", "reverseHolofoil", "1stEditionHolofoil"]:
            for key in ["market", "mid", "low"]:
                price = prices.get(variant, {}).get(key)
                if price and price > 0:
                    return price
        return None

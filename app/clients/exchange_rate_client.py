"""
Exchange rate client stub.
The business uses manual rate updates via admin panel.
This client can be extended to fetch from a free API if needed.
"""
import httpx
from cachetools import TTLCache


class ExchangeRateClient:
    """Fetches USD to ZAR exchange rate from a public API."""
    API_URL = "https://open.er-api.com/v6/latest/USD"

    def __init__(self):
        self._cache = TTLCache(maxsize=1, ttl=86400)  # 24 hours

    async def get_usd_to_zar(self) -> float | None:
        """Fetch current USD/ZAR rate. Returns None on failure."""
        if "rate" in self._cache:
            return self._cache["rate"]

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.API_URL, timeout=10.0)
                if resp.status_code == 200:
                    rate = resp.json().get("rates", {}).get("ZAR")
                    if rate:
                        self._cache["rate"] = float(rate)
                        return float(rate)
        except Exception:
            pass
        return None

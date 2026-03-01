import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.domain.models.exchange_rate import ExchangeRate

logger = logging.getLogger(__name__)

STALE_THRESHOLD = timedelta(hours=24)


async def fetch_exchange_rate() -> float:
    """Fetch live USD->ZAR rate from exchangerate-api.com."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://api.exchangerate-api.com/v4/latest/USD"
        )
        resp.raise_for_status()
    data = resp.json()
    return float(data["rates"]["ZAR"])


async def get_current_rate(db: AsyncSession) -> float:
    """Get current USD->ZAR exchange rate.

    Checks DB cache first (24h TTL), then fetches live,
    then falls back to settings.usd_to_zar.
    """
    settings = get_settings()

    result = await db.execute(
        select(ExchangeRate)
        .where(
            ExchangeRate.from_currency == "USD",
            ExchangeRate.to_currency == "ZAR",
        )
        .order_by(desc(ExchangeRate.fetched_at))
        .limit(1)
    )
    latest = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if latest is not None:
        fetched = latest.fetched_at
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        if now - fetched < STALE_THRESHOLD:
            return float(latest.rate)

    try:
        new_rate = await fetch_exchange_rate()
    except Exception:
        logger.warning("Failed to fetch live exchange rate, using fallback")
        if latest is not None:
            return float(latest.rate)
        return settings.usd_to_zar

    rate_record = ExchangeRate(
        from_currency="USD",
        to_currency="ZAR",
        rate=new_rate,
    )
    db.add(rate_record)
    await db.flush()
    return new_rate

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.domain.models.exchange_rate import ExchangeRate


class ExchangeRateRepository(BaseRepository[ExchangeRate]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ExchangeRate)

    async def get_latest(self, from_currency: str, to_currency: str) -> ExchangeRate | None:
        result = await self.db.execute(
            select(ExchangeRate)
            .where(
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
            )
            .order_by(ExchangeRate.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

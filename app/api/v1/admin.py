from fastapi import APIRouter, Depends
from app.api.deps import require_seller
from app.repositories.exchange_rate_repo import ExchangeRateRepository
from app.domain.models.exchange_rate import ExchangeRate
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["Admin"])


class ExchangeRateUpdate(BaseModel):
    rate: float


@router.get("/exchange-rate")
async def get_rate(user=Depends(require_seller), db: AsyncSession = Depends(get_db)):
    repo = ExchangeRateRepository(db)
    rate = await repo.get_latest("USD", "ZAR")
    return {"rate": rate.rate if rate else 18.50, "source": rate.source if rate else "default"}


@router.put("/exchange-rate")
async def set_rate(data: ExchangeRateUpdate, user=Depends(require_seller), db: AsyncSession = Depends(get_db)):
    repo = ExchangeRateRepository(db)
    rate = ExchangeRate(from_currency="USD", to_currency="ZAR", rate=data.rate, source="manual")
    await repo.create(rate)
    return {"rate": data.rate, "source": "manual"}

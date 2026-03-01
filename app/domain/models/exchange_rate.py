from datetime import datetime
from decimal import Decimal
from sqlalchemy import Integer, String, Numeric, DateTime, text
from sqlalchemy.orm import Mapped, mapped_column
from app.domain.models.base import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_currency: Mapped[str] = mapped_column(
        String(3), default="USD", server_default="USD"
    )
    to_currency: Mapped[str] = mapped_column(
        String(3), default="ZAR", server_default="ZAR"
    )
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

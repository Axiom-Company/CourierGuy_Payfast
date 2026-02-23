from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.domain.models.base import Base, UUIDMixin, TimestampMixin


class ExchangeRate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "exchange_rates"

    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)

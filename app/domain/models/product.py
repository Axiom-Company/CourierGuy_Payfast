from sqlalchemy import String, Float, Integer, Text, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.domain.models.base import Base, UUIDMixin, TimestampMixin
from app.domain.enums import ProductType, SealedCategory, CardCondition


class Product(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "products"

    # ── Core (both types) ──
    product_type: Mapped[ProductType] = mapped_column(SQLEnum(ProductType), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    # Values: active | sold_out | delisted

    # ── Sealed product fields ──
    sealed_category: Mapped[SealedCategory | None] = mapped_column(SQLEnum(SealedCategory), nullable=True)
    set_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Single card fields ──
    tcg_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    card_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    set_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rarity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    card_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hp: Mapped[str | None] = mapped_column(String(10), nullable=True)
    artist: Mapped[str | None] = mapped_column(String(100), nullable=True)
    condition: Mapped[CardCondition | None] = mapped_column(SQLEnum(CardCondition), nullable=True)
    condition_multiplier: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Images ──
    tcg_image_small: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tcg_image_large: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_public_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Pricing ──
    market_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_price_zar: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost_price_zar: Mapped[float | None] = mapped_column(Float, nullable=True)
    margin_percent: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)
    sell_price_zar: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Stock ──
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    quantity_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Weight (for shipping quotes) ──
    weight_grams: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # ── Seller ──
    listed_by: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        Index("idx_product_search", "name", "set_name", "product_type", "status"),
        Index("idx_product_type_status", "product_type", "status"),
    )

    @property
    def available_quantity(self) -> int:
        return self.quantity - self.quantity_sold

    @property
    def is_in_stock(self) -> bool:
        return self.available_quantity > 0

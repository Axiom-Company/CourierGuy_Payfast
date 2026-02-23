from pydantic import BaseModel, Field
from app.domain.enums import ProductType, SealedCategory, CardCondition


# ── Create Requests ──

class SealedProductCreate(BaseModel):
    """List a new sealed product (booster box, pack, ETB, etc.)."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    sealed_category: SealedCategory
    set_name: str | None = None
    cost_price_zar: float | None = Field(None, ge=0)
    sell_price_zar: float = Field(..., gt=0)
    quantity: int = Field(1, ge=1)
    weight_grams: int = Field(500, ge=1)


class SingleCardCreate(BaseModel):
    """List a single card — system fetches all data from pokemontcg.io via tcg_id."""
    tcg_id: str = Field(..., min_length=1, max_length=50)
    condition: CardCondition
    cost_price_zar: float | None = Field(None, ge=0)
    margin_percent: float = Field(30.0, ge=0, le=200)
    quantity: int = Field(1, ge=1)


class ProductUpdate(BaseModel):
    """Partial update for any product."""
    sell_price_zar: float | None = Field(None, gt=0)
    quantity: int | None = Field(None, ge=0)
    status: str | None = None
    description: str | None = None
    condition: CardCondition | None = None
    margin_percent: float | None = Field(None, ge=0, le=200)


# ── Responses ──

class ProductResponse(BaseModel):
    """Full product detail — used on product detail page."""
    id: str
    product_type: ProductType
    name: str
    description: str | None
    status: str
    sealed_category: SealedCategory | None
    set_name: str | None
    tcg_id: str | None
    card_number: str | None
    set_id: str | None
    rarity: str | None
    card_type: str | None
    hp: str | None
    artist: str | None
    condition: CardCondition | None
    condition_multiplier: float | None
    tcg_image_small: str | None
    tcg_image_large: str | None
    photo_url: str | None
    market_price_usd: float | None
    market_price_zar: float | None
    cost_price_zar: float | None
    margin_percent: float
    sell_price_zar: float
    quantity: int
    quantity_sold: int
    available_quantity: int
    is_in_stock: bool
    weight_grams: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Lightweight response for browse/grid views — fewer fields = faster."""
    id: str
    product_type: ProductType
    name: str
    set_name: str | None
    sealed_category: SealedCategory | None
    condition: CardCondition | None
    rarity: str | None
    tcg_image_small: str | None
    photo_url: str | None
    sell_price_zar: float
    available_quantity: int
    is_in_stock: bool
    created_at: str

    class Config:
        from_attributes = True


class PriceCheckResponse(BaseModel):
    """Returned when seller checks pricing before listing a card."""
    tcg_id: str
    card_name: str
    set_name: str
    rarity: str | None
    tcg_image_small: str | None
    tcg_image_large: str | None
    market_price_usd: float | None
    exchange_rate: float
    market_price_zar: float | None
    condition: str
    condition_multiplier: float
    adjusted_market_zar: float
    margin_percent: float
    sell_price_zar: float
    cost_price_zar: float | None
    profit_zar: float | None


class InventoryStatsResponse(BaseModel):
    """Dashboard stats for seller."""
    total_products_listed: int
    total_in_stock: int
    total_sold: int
    stock_value_zar: float
    total_revenue_zar: float
    total_profit_zar: float

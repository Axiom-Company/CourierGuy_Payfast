from pydantic import BaseModel, Field


class CartItemAdd(BaseModel):
    product_id: str
    quantity: int = Field(1, ge=1, le=10)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1, le=10)


class CartItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    product_type: str
    condition: str | None
    sell_price_zar: float
    quantity: int
    line_total_zar: float
    tcg_image_small: str | None
    photo_url: str | None
    is_in_stock: bool
    available_quantity: int


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    item_count: int
    subtotal_zar: float
    total_weight_grams: int

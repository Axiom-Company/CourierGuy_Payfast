from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.repositories.base import BaseRepository
from app.domain.models.cart import CartItem


class CartRepository(BaseRepository[CartItem]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, CartItem)

    async def get_user_cart(self, user_id: str) -> list[CartItem]:
        result = await self.db.execute(
            select(CartItem)
            .options(selectinload(CartItem.product))
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_user_cart_item(self, user_id: str, product_id: str) -> CartItem | None:
        result = await self.db.execute(
            select(CartItem).where(
                CartItem.user_id == user_id,
                CartItem.product_id == product_id,
            )
        )
        return result.scalar_one_or_none()

    async def clear_user_cart(self, user_id: str) -> None:
        await self.db.execute(delete(CartItem).where(CartItem.user_id == user_id))
        await self.db.flush()

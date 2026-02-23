from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.repositories.base import BaseRepository
from app.domain.models.order import Order, OrderItem
from app.domain.enums import OrderStatus


class OrderRepository(BaseRepository[Order]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Order)

    async def get_by_id_with_items(self, id: str) -> Order | None:
        result = await self.db.execute(
            select(Order).options(selectinload(Order.items)).where(Order.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_order_number(self, order_number: str) -> Order | None:
        result = await self.db.execute(
            select(Order).options(selectinload(Order.items)).where(Order.order_number == order_number)
        )
        return result.scalar_one_or_none()

    async def get_by_tracking_number(self, tracking_number: str) -> Order | None:
        result = await self.db.execute(
            select(Order).where(Order.courier_tracking_number == tracking_number)
        )
        return result.scalar_one_or_none()

    async def get_customer_orders(self, customer_id: str):
        return (
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
        )

    async def get_all_orders(self, status: OrderStatus | None = None):
        query = select(Order).options(selectinload(Order.items))
        if status:
            query = query.where(Order.order_status == status)
        return query.order_by(Order.created_at.desc())

    async def get_next_order_number(self) -> str:
        count = await self.db.scalar(select(func.count()).select_from(Order)) or 0
        return f"PKM-{(count + 1):05d}"

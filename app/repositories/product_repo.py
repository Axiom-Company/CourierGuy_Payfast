from sqlalchemy import select, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.domain.models.product import Product
from app.domain.enums import ProductType, CardCondition


class ProductRepository(BaseRepository[Product]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Product)

    async def browse(
        self,
        q: str | None = None,
        product_type: ProductType | None = None,
        sealed_category: str | None = None,
        set_name: str | None = None,
        rarity: str | None = None,
        condition: CardCondition | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sort: str = "newest",
    ):
        """Build a filtered query for the public store browse endpoint."""
        query = select(Product).where(Product.status == "active")

        if q:
            search = f"%{q}%"
            query = query.where(
                or_(
                    Product.name.ilike(search),
                    Product.set_name.ilike(search),
                    Product.rarity.ilike(search),
                )
            )
        if product_type:
            query = query.where(Product.product_type == product_type)
        if sealed_category:
            query = query.where(Product.sealed_category == sealed_category)
        if set_name:
            query = query.where(Product.set_name.ilike(f"%{set_name}%"))
        if rarity:
            query = query.where(Product.rarity == rarity)
        if condition:
            query = query.where(Product.condition == condition)
        if min_price is not None:
            query = query.where(Product.sell_price_zar >= min_price)
        if max_price is not None:
            query = query.where(Product.sell_price_zar <= max_price)

        # Sorting
        sort_map = {
            "newest": Product.created_at.desc(),
            "price_asc": Product.sell_price_zar.asc(),
            "price_desc": Product.sell_price_zar.desc(),
            "name_asc": Product.name.asc(),
        }
        query = query.order_by(sort_map.get(sort, Product.created_at.desc()))
        return query

    async def get_featured(self, limit: int = 8) -> list[Product]:
        result = await self.db.execute(
            select(Product)
            .where(Product.status == "active")
            .order_by(Product.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_seller(self, seller_id: str, q: str | None = None, status: str | None = None):
        """Build inventory query for seller dashboard."""
        query = select(Product).where(Product.listed_by == seller_id)
        if q:
            query = query.where(Product.name.ilike(f"%{q}%"))
        if status:
            query = query.where(Product.status == status)
        return query.order_by(Product.created_at.desc())

    async def get_inventory_stats(self, seller_id: str) -> dict:
        """Aggregate stats for seller dashboard."""
        base = select(Product).where(Product.listed_by == seller_id)

        total_listed = await self.db.scalar(
            select(func.count()).select_from(base.subquery())
        ) or 0

        in_stock = await self.db.scalar(
            select(func.count()).select_from(
                base.where(Product.status == "active").subquery()
            )
        ) or 0

        total_sold = await self.db.scalar(
            select(func.coalesce(func.sum(Product.quantity_sold), 0))
            .where(Product.listed_by == seller_id)
        ) or 0

        stock_value = await self.db.scalar(
            select(func.coalesce(
                func.sum(Product.sell_price_zar * (Product.quantity - Product.quantity_sold)), 0
            )).where(Product.listed_by == seller_id, Product.status == "active")
        ) or 0.0

        revenue = await self.db.scalar(
            select(func.coalesce(
                func.sum(Product.sell_price_zar * Product.quantity_sold), 0
            )).where(Product.listed_by == seller_id)
        ) or 0.0

        profit = await self.db.scalar(
            select(func.coalesce(
                func.sum(
                    (Product.sell_price_zar - func.coalesce(Product.cost_price_zar, 0)) * Product.quantity_sold
                ), 0
            )).where(Product.listed_by == seller_id)
        ) or 0.0

        return {
            "total_products_listed": total_listed,
            "total_in_stock": in_stock,
            "total_sold": total_sold,
            "stock_value_zar": round(float(stock_value), 2),
            "total_revenue_zar": round(float(revenue), 2),
            "total_profit_zar": round(float(profit), 2),
        }

    async def reduce_stock(self, product_id: str, quantity: int) -> None:
        """Atomically reduce stock after purchase."""
        await self.db.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(quantity_sold=Product.quantity_sold + quantity)
        )
        await self.db.flush()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.domain.models.user import Customer


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Customer)

    async def get_by_email(self, email: str) -> Customer | None:
        result = await self.db.execute(select(Customer).where(Customer.email == email))
        return result.scalar_one_or_none()

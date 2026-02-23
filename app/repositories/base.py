from typing import TypeVar, Generic, Type
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic repository with standard CRUD operations."""

    def __init__(self, db: AsyncSession, model: Type[T]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: str) -> T | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        result = await self.db.execute(
            select(self.model).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, entity: T) -> T:
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def update_by_id(self, id: str, values: dict) -> T | None:
        await self.db.execute(
            update(self.model).where(self.model.id == id).values(**values)
        )
        await self.db.flush()
        return await self.get_by_id(id)

    async def delete_by_id(self, id: str) -> None:
        await self.db.execute(delete(self.model).where(self.model.id == id))
        await self.db.flush()

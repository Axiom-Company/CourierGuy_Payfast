from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.domain.models.user import Profile


class ProfileRepository(BaseRepository[Profile]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Profile)

    async def get_by_email(self, email: str) -> Profile | None:
        result = await self.db.execute(select(Profile).where(Profile.email == email))
        return result.scalar_one_or_none()

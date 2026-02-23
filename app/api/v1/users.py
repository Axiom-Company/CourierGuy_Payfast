from fastapi import APIRouter, Depends
from app.domain.schemas.user import UserProfileResponse, UserProfileUpdate
from app.domain.models.user import User
from app.repositories.user_repo import UserRepository
from app.api.deps import get_current_user
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=UserProfileResponse)
async def update_me(
    data: UserProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    updated = await repo.update_by_id(user.id, data.model_dump(exclude_unset=True))
    return updated

from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt

from app.config import get_settings
from app.database import get_db
from app.domain.models.user import Profile


async def get_current_user_id(
    authorization: str = Header(..., description="Bearer <supabase-access-token>"),
) -> str:
    """Decode Supabase JWT and return the user ID (sub claim).
    Does NOT hit the database — use when you only need the UUID."""
    settings = get_settings()
    token = authorization.removeprefix("Bearer ").strip()

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Token missing sub claim")
    return user_id


async def get_current_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Profile:
    """Load the full Profile row for the authenticated user."""
    result = await db.execute(select(Profile).where(Profile.id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(404, "Profile not found")
    return profile


async def require_seller(
    profile: Profile = Depends(get_current_profile),
) -> Profile:
    """Require the authenticated user to be a seller."""
    if not profile.is_seller:
        raise HTTPException(403, "Seller access required")
    return profile


async def require_admin(
    profile: Profile = Depends(get_current_profile),
) -> Profile:
    """Require the authenticated user to be an admin."""
    if not profile.is_admin:
        raise HTTPException(403, "Admin access required")
    return profile


async def optional_current_user_id(
    authorization: str | None = Header(None),
) -> str | None:
    """Returns user ID if a valid token is present, None otherwise.
    Use for endpoints that work for both guests and logged-in users."""
    if not authorization:
        return None
    settings = get_settings()
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None

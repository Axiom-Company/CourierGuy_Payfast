import math
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.schemas.common import PaginatedResponse


async def paginate(
    db: AsyncSession,
    query,
    page: int,
    page_size: int,
    response_model=None,
) -> PaginatedResponse:
    """Generic pagination helper for any SQLAlchemy query."""
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    paginated_query = query.offset(offset).limit(page_size)
    result = await db.execute(paginated_query)
    items = result.scalars().all()

    # Convert to response model if provided
    if response_model:
        items = [response_model.model_validate(item) for item in items]

    return PaginatedResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total_count / page_size) if page_size > 0 else 0,
    )

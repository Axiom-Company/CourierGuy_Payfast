from fastapi import APIRouter, Depends, Query, HTTPException
from app.domain.schemas.product import ProductListResponse, ProductResponse
from app.domain.schemas.common import PaginatedResponse
from app.domain.enums import ProductType, CardCondition
from app.services.product_service import ProductService
from app.api.deps import get_product_service
from app.utils.pagination import paginate
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/store", tags=["Store"])


@router.get("/products", response_model=PaginatedResponse[ProductListResponse])
async def browse(
    q: str | None = Query(None),
    product_type: ProductType | None = Query(None),
    sealed_category: str | None = Query(None),
    set_name: str | None = Query(None),
    rarity: str | None = Query(None),
    condition: CardCondition | None = Query(None),
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    sort: str = Query("newest", pattern="^(newest|price_asc|price_desc|name_asc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    service: ProductService = Depends(get_product_service),
    db: AsyncSession = Depends(get_db),
):
    query = await service.browse_query(
        q=q, product_type=product_type, sealed_category=sealed_category,
        set_name=set_name, rarity=rarity, condition=condition,
        min_price=min_price, max_price=max_price, sort=sort,
    )
    return await paginate(db, query, page, page_size, ProductListResponse)


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, service: ProductService = Depends(get_product_service)):
    product = await service.get_by_id(product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@router.get("/featured", response_model=list[ProductListResponse])
async def featured(limit: int = Query(8, ge=1, le=20), service: ProductService = Depends(get_product_service)):
    products = await service.get_featured(limit)
    return [ProductListResponse.model_validate(p) for p in products]


@router.get("/sets")
async def get_sets(service: ProductService = Depends(get_product_service)):
    return await service.get_sets()

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from app.domain.schemas.product import (
    SealedProductCreate, SingleCardCreate, ProductUpdate, ProductResponse, PriceCheckResponse,
)
from app.domain.schemas.common import PaginatedResponse
from app.services.product_service import ProductService
from app.services.image_service import ImageService
from app.api.deps import get_product_service, get_image_service, require_seller
from app.domain.models.user import User
from app.utils.pagination import paginate
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/products", tags=["Seller Products"])


@router.post("/sealed", response_model=ProductResponse, status_code=201)
async def list_sealed(data: SealedProductCreate, user: User = Depends(require_seller),
                      service: ProductService = Depends(get_product_service)):
    return await service.create_sealed(data, user.id)


@router.post("/single", response_model=ProductResponse, status_code=201)
async def list_single(data: SingleCardCreate, user: User = Depends(require_seller),
                      service: ProductService = Depends(get_product_service)):
    try:
        return await service.create_single(data, user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{product_id}/photo")
async def upload_photo(product_id: str, file: UploadFile = File(...),
                       user: User = Depends(require_seller),
                       product_service: ProductService = Depends(get_product_service),
                       image_service: ImageService = Depends(get_image_service)):
    product = await product_service.get_by_id(product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    result = await image_service.upload_product_photo(file, product_id)
    await product_service.update(product_id, {"photo_url": result["url"], "photo_public_id": result["public_id"]})
    return result


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: str, data: ProductUpdate, user: User = Depends(require_seller),
                         service: ProductService = Depends(get_product_service)):
    product = await service.update(product_id, data.model_dump(exclude_unset=True))
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@router.delete("/{product_id}", status_code=204)
async def delist(product_id: str, user: User = Depends(require_seller),
                 service: ProductService = Depends(get_product_service)):
    await service.delist(product_id)


@router.get("/inventory", response_model=PaginatedResponse)
async def inventory(q: str | None = None, status: str | None = None,
                    page: int = 1, page_size: int = 50,
                    user: User = Depends(require_seller),
                    service: ProductService = Depends(get_product_service),
                    db: AsyncSession = Depends(get_db)):
    query = await service.inventory_query(user.id, q, status)
    return await paginate(db, query, page, page_size, ProductResponse)


@router.get("/inventory/stats")
async def inventory_stats(user: User = Depends(require_seller),
                          service: ProductService = Depends(get_product_service)):
    return await service.get_inventory_stats(user.id)


@router.get("/search-tcg")
async def search_tcg(q: str, service: ProductService = Depends(get_product_service)):
    return await service.search_tcg_cards(q)


@router.get("/price-check/{tcg_id}")
async def price_check(tcg_id: str, condition: str = "NM", margin: float = 30.0,
                      cost: float | None = None,
                      service: ProductService = Depends(get_product_service)):
    return await service.get_price_check(tcg_id, condition, margin, cost)

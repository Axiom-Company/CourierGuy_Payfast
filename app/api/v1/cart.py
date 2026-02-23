from fastapi import APIRouter, Depends, HTTPException
from app.domain.schemas.cart import CartItemAdd, CartItemUpdate, CartResponse
from app.services.cart_service import CartService
from app.api.deps import get_cart_service, get_current_user
from app.domain.models.user import User

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("", response_model=CartResponse)
async def get_cart(user: User = Depends(get_current_user), service: CartService = Depends(get_cart_service)):
    return await service.get_cart(user.id)


@router.post("/add")
async def add_to_cart(data: CartItemAdd, user: User = Depends(get_current_user),
                      service: CartService = Depends(get_cart_service)):
    try:
        return await service.add_item(user.id, data.product_id, data.quantity)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/{item_id}")
async def update_cart_item(item_id: str, data: CartItemUpdate,
                           user: User = Depends(get_current_user),
                           service: CartService = Depends(get_cart_service)):
    return await service.update_item(item_id, data.quantity)


@router.delete("/{item_id}", status_code=204)
async def remove_item(item_id: str, user: User = Depends(get_current_user),
                      service: CartService = Depends(get_cart_service)):
    await service.remove_item(item_id)


@router.delete("/clear", status_code=204)
async def clear_cart(user: User = Depends(get_current_user),
                     service: CartService = Depends(get_cart_service)):
    await service.clear_cart(user.id)

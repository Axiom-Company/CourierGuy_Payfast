from fastapi import APIRouter
from app.api.v1 import auth, users, products, store, cart, checkout, orders, shipping, admin

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(products.router)
api_router.include_router(store.router)
api_router.include_router(cart.router)
api_router.include_router(checkout.router)
api_router.include_router(orders.router)
api_router.include_router(shipping.router)
api_router.include_router(admin.router)

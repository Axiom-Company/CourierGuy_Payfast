from fastapi import APIRouter
from app.api.v1 import checkout, orders, shipping, dashboard, cards, marketplace, promotions
from app.payments.payflex.router import router as payflex_router

api_router = APIRouter()
api_router.include_router(checkout.router)
api_router.include_router(orders.router)
api_router.include_router(shipping.router)
api_router.include_router(dashboard.router)
api_router.include_router(payflex_router)
api_router.include_router(cards.router)
api_router.include_router(marketplace.router)
api_router.include_router(promotions.router)

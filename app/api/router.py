from fastapi import APIRouter
from app.api.v1 import checkout, orders, shipping, dashboard
from app.payments.payflex.router import router as payflex_router

api_router = APIRouter()
api_router.include_router(checkout.router)
api_router.include_router(orders.router)
api_router.include_router(shipping.router)
api_router.include_router(dashboard.router)
api_router.include_router(payflex_router)

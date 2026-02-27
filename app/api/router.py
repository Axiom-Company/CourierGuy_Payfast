from fastapi import APIRouter
from app.api.v1 import checkout, orders, shipping, dashboard

api_router = APIRouter()
api_router.include_router(checkout.router)
api_router.include_router(orders.router)
api_router.include_router(shipping.router)
api_router.include_router(dashboard.router)

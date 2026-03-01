from fastapi import Depends, Header, HTTPException
from app.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

from app.clients.payfast_client import PayFastClient
from app.clients.courier_guy_client import CourierGuyClient

from app.repositories.user_repo import UserRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.cart_repo import CartRepository

from app.services.pricing_service import PricingService
from app.services.order_service import OrderService
from app.services.shipping_service import ShippingService
from app.services.payment_service import PaymentService
from app.services.dashboard_service import DashboardService


async def require_admin_api_key(x_admin_api_key: str = Header(...)):
    settings = get_settings()
    if not settings.admin_api_key or x_admin_api_key != settings.admin_api_key:
        raise HTTPException(403, "Invalid admin API key")


# ── Service Factories ──

def get_pricing_service() -> PricingService:
    return PricingService()


def get_shipping_service(db: AsyncSession = Depends(get_db),
                         pricing: PricingService = Depends(get_pricing_service)) -> ShippingService:
    return ShippingService(CourierGuyClient(), OrderRepository(db), pricing)


def get_payment_service(db: AsyncSession = Depends(get_db),
                        shipping: ShippingService = Depends(get_shipping_service)) -> PaymentService:
    return PaymentService(PayFastClient(), OrderRepository(db), ProductRepository(db), shipping)


def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(OrderRepository(db), CartRepository(db), ProductRepository(db))


def get_dashboard_service(db: AsyncSession = Depends(get_db)) -> DashboardService:
    return DashboardService(db)

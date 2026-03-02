from fastapi import Depends, Header, HTTPException
from app.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

from app.clients.payfast_client import PayFastClient
from app.clients.courier_guy_client import CourierGuyClient

from app.repositories.user_repo import CustomerRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.cart_repo import CartRepository
from app.repositories.marketplace_repo import MarketplaceRepository

from app.services.pricing_service import PricingService
from app.services.order_service import OrderService
from app.services.shipping_service import ShippingService
from app.services.payment_service import PaymentService
from app.services.dashboard_service import DashboardService
from app.services.marketplace_payment_service import MarketplacePaymentService
from app.services.email_service import EmailService

# Re-export auth dependencies for convenience
from app.api.auth import (  # noqa: F401
    get_current_user_id,
    get_current_customer,
    require_seller,
    optional_current_user_id,
)


async def require_admin_api_key(x_admin_api_key: str = Header(...)):
    """Legacy admin API key check — kept for server-to-server / webhook calls."""
    settings = get_settings()
    if not settings.admin_api_key or x_admin_api_key != settings.admin_api_key:
        raise HTTPException(403, "Invalid admin API key")


# ── Service Factories ──

def get_pricing_service() -> PricingService:
    return PricingService()


def get_email_service(db: AsyncSession = Depends(get_db)) -> EmailService:
    settings = get_settings()
    return EmailService(
        api_key=settings.zeptomail_api_key,
        from_email=settings.zeptomail_from_email,
        from_name=settings.zeptomail_from_name,
        bounce_email=settings.zeptomail_bounce_email,
        db=db,
    )


def get_shipping_service(
    db: AsyncSession = Depends(get_db),
    pricing: PricingService = Depends(get_pricing_service),
    email: EmailService = Depends(get_email_service),
) -> ShippingService:
    return ShippingService(CourierGuyClient(), OrderRepository(db), pricing, email)


def get_payment_service(
    db: AsyncSession = Depends(get_db),
    shipping: ShippingService = Depends(get_shipping_service),
    email: EmailService = Depends(get_email_service),
) -> PaymentService:
    return PaymentService(PayFastClient(), OrderRepository(db), ProductRepository(db), shipping, email)


def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(OrderRepository(db), CartRepository(db), ProductRepository(db))


def get_dashboard_service(db: AsyncSession = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


def get_marketplace_repo(db: AsyncSession = Depends(get_db)) -> MarketplaceRepository:
    return MarketplaceRepository(db)


def get_marketplace_payment_service(
    db: AsyncSession = Depends(get_db),
) -> MarketplacePaymentService:
    settings = get_settings()
    return MarketplacePaymentService(
        PayFastClient(),
        MarketplaceRepository(db),
        EmailService(
            api_key=settings.zeptomail_api_key,
            from_email=settings.zeptomail_from_email,
            from_name=settings.zeptomail_from_name,
            bounce_email=settings.zeptomail_bounce_email,
            db=db,
        ),
    )

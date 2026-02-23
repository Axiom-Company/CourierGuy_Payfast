from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.utils.security import decode_token
from app.domain.models.user import User
from app.domain.enums import UserRole

from app.clients.pokemon_tcg_client import PokemonTCGClient
from app.clients.payfast_client import PayFastClient
from app.clients.courier_guy_client import CourierGuyClient
from app.clients.cloudinary_client import CloudinaryClient

from app.repositories.user_repo import UserRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.order_repo import OrderRepository
from app.repositories.cart_repo import CartRepository
from app.repositories.exchange_rate_repo import ExchangeRateRepository

from app.services.auth_service import AuthService
from app.services.product_service import ProductService
from app.services.pricing_service import PricingService
from app.services.order_service import OrderService
from app.services.cart_service import CartService
from app.services.shipping_service import ShippingService
from app.services.payment_service import PaymentService
from app.services.image_service import ImageService

security = HTTPBearer(auto_error=False)


# ── Auth ──

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security),
                           db: AsyncSession = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(401, "Not authenticated")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid token")
    user = await UserRepository(db).get_by_id(payload["sub"])
    if not user:
        raise HTTPException(401, "User not found")
    return user


async def get_current_user_optional(credentials: HTTPAuthorizationCredentials | None = Depends(security),
                                    db: AsyncSession = Depends(get_db)) -> User | None:
    if not credentials:
        return None
    payload = decode_token(credentials.credentials)
    if not payload:
        return None
    return await UserRepository(db).get_by_id(payload.get("sub", ""))


async def require_seller(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.SELLER, UserRole.ADMIN):
        raise HTTPException(403, "Seller access required")
    return user


# ── Service Factories ──

def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(UserRepository(db))


def get_pricing_service(db: AsyncSession = Depends(get_db)) -> PricingService:
    return PricingService(PokemonTCGClient(), ExchangeRateRepository(db))


def get_product_service(db: AsyncSession = Depends(get_db),
                        pricing: PricingService = Depends(get_pricing_service)) -> ProductService:
    return ProductService(ProductRepository(db), PokemonTCGClient(), pricing)


def get_cart_service(db: AsyncSession = Depends(get_db)) -> CartService:
    return CartService(CartRepository(db), ProductRepository(db))


def get_shipping_service(db: AsyncSession = Depends(get_db),
                         pricing: PricingService = Depends(get_pricing_service)) -> ShippingService:
    return ShippingService(CourierGuyClient(), OrderRepository(db), pricing)


def get_payment_service(db: AsyncSession = Depends(get_db),
                        shipping: ShippingService = Depends(get_shipping_service)) -> PaymentService:
    return PaymentService(PayFastClient(), OrderRepository(db), ProductRepository(db), shipping)


def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(OrderRepository(db), CartRepository(db), ProductRepository(db))


def get_image_service() -> ImageService:
    return ImageService(CloudinaryClient())

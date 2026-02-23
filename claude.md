# CLAUDE.md — Pokemon Card Store Backend

## Complete Build Specification for Claude Code

---

## PROJECT OVERVIEW

Build a production-ready FastAPI backend for a South African Pokemon card reselling business.
The store sells **sealed products** (booster boxes, packs, ETBs) and **single cards** (graded by condition with market-based pricing).

**Business context:**

* Two partners (Brandon + Ruben) running a Pty Ltd in South Africa
* All prices in ZAR (South African Rand)
* Payments via PayFast (SA payment gateway)
* Shipping via The Courier Guy API (collection from seller address, door-to-door delivery)
* Card pricing data from pokemontcg.io API
* Images hosted on Cloudinary
* Frontend is a separate React app (communicates via REST API)
* Accounting in Gimbla (manual recording — no API integration needed)

---

## ARCHITECTURE PRINCIPLES

### SOLID + Clean Architecture (Layered)

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (Routers)                    │
│  Thin controllers — validate input, call services, return   │
├─────────────────────────────────────────────────────────────┤
│                    Service Layer (Business Logic)            │
│  All business rules live here. No direct DB or API calls.   │
│  Services depend on repository/client abstractions.         │
├─────────────────────────────────────────────────────────────┤
│                    Repository Layer (Data Access)            │
│  All database queries. Returns domain models only.          │
├─────────────────────────────────────────────────────────────┤
│                    Client Layer (External APIs)              │
│  PayFast, Courier Guy, pokemontcg.io, Cloudinary wrappers  │
├─────────────────────────────────────────────────────────────┤
│                    Domain Layer (Models + Schemas)           │
│  Pydantic schemas, SQLAlchemy models, enums, constants      │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

* **Dependency Injection** via FastAPI `Depends()` — every service receives dependencies via constructor. Makes testing trivial (swap real for mocks).
* **Single Responsibility** — each file does ONE thing. Routers don't contain logic. Services don't touch the DB directly. Repos don't know about HTTP.
* **Open/Closed** — new product types or shipping providers can be added without modifying existing code.
* **Interface Segregation** — schemas are split: lightweight `ListResponse` for grids, full `DetailResponse` for product pages.
* **Async everywhere** — all DB queries, HTTP calls, and route handlers are async for maximum concurrency.

```python
# Dependency injection pattern used throughout
class ProductService:
    def __init__(self, repo: ProductRepository, pokemon_client: PokemonTCGClient, pricing: PricingService):
        self.repo = repo
        self.pokemon_client = pokemon_client
        self.pricing = pricing

def get_product_service(
    db: AsyncSession = Depends(get_db),
    pricing: PricingService = Depends(get_pricing_service),
) -> ProductService:
    return ProductService(ProductRepository(db), PokemonTCGClient(), pricing)
```

---

## TECH STACK

| Component        | Technology                   | Version | Why                               |
| ---------------- | ---------------------------- | ------- | --------------------------------- |
| Framework        | FastAPI (async)              | 0.115+  | Auto-docs, Pydantic, async native |
| Database         | PostgreSQL via Supabase      | 15+     | Free tier, managed, reliable      |
| ORM              | SQLAlchemy 2.0 (async)       | 2.0.35+ | Industry standard async ORM       |
| Migrations       | Alembic                      | 1.13+   | Schema versioning                 |
| Auth             | JWT via python-jose + bcrypt | —      | Stateless auth                    |
| Validation       | Pydantic v2                  | 2.9+    | Built into FastAPI                |
| HTTP Client      | httpx (async)                | 0.27+   | External API calls                |
| Caching          | cachetools (in-memory TTL)   | 5.5+    | Cache card data, exchange rates   |
| Image Upload     | Cloudinary SDK               | 1.41+   | Free 25GB tier                    |
| Background Tasks | FastAPI BackgroundTasks      | —      | Post-payment processing           |
| Testing          | pytest + pytest-asyncio      | —      | Async test support                |
| Linting          | ruff                         | 0.6+    | Fast, all-in-one                  |

---

## PROJECT STRUCTURE

```
pokemon-store-api/
├── alembic/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI app factory + lifespan
│   ├── config.py                      # Pydantic settings from .env
│   ├── database.py                    # Async engine + session factory
│   │
│   ├── domain/                        # === DOMAIN LAYER ===
│   │   ├── __init__.py
│   │   ├── enums.py                   # ProductType, Condition, OrderStatus, etc.
│   │   ├── constants.py               # Condition multipliers, shipping defaults
│   │   ├── models/                    # SQLAlchemy ORM models
│   │   │   ├── __init__.py            # Re-export all models
│   │   │   ├── base.py               # DeclarativeBase + UUID/Timestamp mixins
│   │   │   ├── user.py
│   │   │   ├── product.py
│   │   │   ├── order.py              # Order + OrderItem
│   │   │   ├── cart.py               # CartItem
│   │   │   └── exchange_rate.py
│   │   └── schemas/                   # Pydantic request/response DTOs
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── user.py
│   │       ├── product.py            # SealedCreate, SingleCreate, ProductResponse, ListResponse
│   │       ├── order.py
│   │       ├── cart.py
│   │       ├── shipping.py
│   │       └── common.py             # PaginatedResponse, ErrorResponse
│   │
│   ├── repositories/                  # === DATA ACCESS LAYER ===
│   │   ├── __init__.py
│   │   ├── base.py                   # BaseRepository[T] with generic CRUD
│   │   ├── user_repo.py
│   │   ├── product_repo.py
│   │   ├── order_repo.py
│   │   ├── cart_repo.py
│   │   └── exchange_rate_repo.py
│   │
│   ├── services/                      # === BUSINESS LOGIC LAYER ===
│   │   ├── __init__.py
│   │   ├── auth_service.py           # Register, login, JWT
│   │   ├── user_service.py           # Profile management
│   │   ├── product_service.py        # List sealed/single, inventory
│   │   ├── pricing_service.py        # Market price, ZAR conversion, margins
│   │   ├── order_service.py          # Create order, status updates
│   │   ├── cart_service.py           # Cart CRUD
│   │   ├── shipping_service.py       # Quote, book, webhook handler
│   │   ├── payment_service.py        # PayFast checkout + ITN handler
│   │   ├── image_service.py          # Cloudinary upload/delete
│   │   └── email_service.py          # Transactional emails
│   │
│   ├── clients/                       # === EXTERNAL API WRAPPERS ===
│   │   ├── __init__.py
│   │   ├── pokemon_tcg_client.py     # pokemontcg.io v2 API
│   │   ├── payfast_client.py         # PayFast payment gateway
│   │   ├── courier_guy_client.py     # The Courier Guy shipping API
│   │   ├── cloudinary_client.py      # Cloudinary image CDN
│   │   └── exchange_rate_client.py   # USD→ZAR fetcher
│   │
│   ├── api/                           # === API ROUTES LAYER ===
│   │   ├── __init__.py
│   │   ├── router.py                 # Aggregates all v1 routers
│   │   ├── deps.py                   # get_current_user, require_seller, service factories
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py               # POST /register, /login
│   │       ├── users.py              # GET/PUT /me
│   │       ├── products.py           # Seller: list/update/delete products
│   │       ├── store.py              # Public: browse, search, detail, featured
│   │       ├── cart.py               # Cart operations
│   │       ├── checkout.py           # Create order + PayFast flow
│   │       ├── orders.py             # Customer + seller order views
│   │       ├── shipping.py           # Quote, book, webhook
│   │       └── admin.py              # Stats, exchange rate, settings
│   │
│   └── utils/
│       ├── __init__.py
│       ├── security.py               # hash_password, verify_password, create/decode JWT
│       ├── pagination.py             # paginate() helper
│       ├── exceptions.py             # NotFoundError, AuthError, etc.
│       └── email_templates.py        # HTML email strings
│
├── tests/
│   ├── conftest.py                    # Test DB, client fixture, auth helpers
│   ├── factories.py                   # Factory functions for test data
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_store.py
│   ├── test_cart.py
│   ├── test_checkout.py
│   ├── test_orders.py
│   └── test_shipping.py
│
├── scripts/
│   ├── seed_data.py                   # Seed test products
│   └── create_seller.py              # Create seller account (Brandon/Ruben)
│
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── render.yaml
├── .env.example
└── README.md
```

---

## ENVIRONMENT VARIABLES

```bash
# .env.example

# ── Database (Supabase Supavisor pooler) ──
# Transaction mode (port 6543) for the app
DATABASE_URL=postgresql+asyncpg://postgres.{ref}:{password}@aws-0-{region}.pooler.supabase.com:6543/postgres
# Session mode (port 5432) for Alembic migrations ONLY
DATABASE_URL_SYNC=postgresql://postgres.{ref}:{password}@aws-0-{region}.pooler.supabase.com:5432/postgres

# ── Auth ──
JWT_SECRET_KEY=generate-a-64-char-random-string-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ── Pokemon TCG API ──
POKEMON_TCG_API_KEY=your-key-from-dev.pokemontcg.io

# ── PayFast ──
PAYFAST_MERCHANT_ID=your-merchant-id
PAYFAST_MERCHANT_KEY=your-merchant-key
PAYFAST_PASSPHRASE=your-passphrase
PAYFAST_SANDBOX=true
PAYFAST_RETURN_URL=https://your-frontend.onrender.com/order/success
PAYFAST_CANCEL_URL=https://your-frontend.onrender.com/cart
PAYFAST_NOTIFY_URL=https://your-api.onrender.com/api/v1/checkout/payfast/notify

# ── The Courier Guy ──
COURIER_GUY_API_KEY=your-api-key
COURIER_GUY_ACCOUNT_NUMBER=your-account-number
COURIER_GUY_WEBHOOK_SECRET=your-webhook-secret

# ── Cloudinary ──
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# ── Exchange Rate ──
USD_TO_ZAR_DEFAULT=18.50

# ── App ──
FRONTEND_URL=https://your-frontend.onrender.com
APP_ENV=production

# ── Seller pickup address (for Courier Guy collection) ──
SELLER_ADDRESS_LINE1=123 Your Street
SELLER_CITY=Vanderbijlpark
SELLER_PROVINCE=Gauteng
SELLER_POSTAL_CODE=1900
SELLER_PHONE=0821234567
SELLER_EMAIL=you@example.com

# ── SMTP (for order emails) ──
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

---

## CONFIG MODULE

```python
# app/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str
    database_url_sync: str = ""

    # Auth
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    # Pokemon TCG
    pokemon_tcg_api_key: str = ""

    # PayFast
    payfast_merchant_id: str
    payfast_merchant_key: str
    payfast_passphrase: str = ""
    payfast_sandbox: bool = True
    payfast_return_url: str
    payfast_cancel_url: str
    payfast_notify_url: str

    # Courier Guy
    courier_guy_api_key: str
    courier_guy_account_number: str = ""
    courier_guy_webhook_secret: str = ""

    # Cloudinary
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    # Exchange Rate
    usd_to_zar_default: float = 18.50

    # App
    frontend_url: str = "http://localhost:5173"
    app_env: str = "development"

    # Seller address (Courier Guy pickup)
    seller_address_line1: str = ""
    seller_city: str = "Vanderbijlpark"
    seller_province: str = "Gauteng"
    seller_postal_code: str = ""
    seller_phone: str = ""
    seller_email: str = ""

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

---

## DATABASE MODULE

```python
# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=(settings.app_env == "development"),
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        # CRITICAL: Required for Supavisor transaction-mode pooling
        "prepared_statement_cache_size": 0,
    },
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

## DOMAIN LAYER

### Enums

```python
# app/domain/enums.py
from enum import Enum

class ProductType(str, Enum):
    SEALED = "sealed"
    SINGLE = "single"

class SealedCategory(str, Enum):
    BOOSTER_BOX = "booster_box"
    BOOSTER_PACK = "booster_pack"
    ETB = "etb"
    COLLECTION = "collection"
    TIN = "tin"
    BUNDLE = "bundle"
    OTHER = "other"

class CardCondition(str, Enum):
    MINT = "Mint"
    NEAR_MINT = "NM"
    LIGHTLY_PLAYED = "LP"
    MODERATELY_PLAYED = "MP"
    HEAVILY_PLAYED = "HP"
    DAMAGED = "Damaged"

class OrderStatus(str, Enum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ShippingMethod(str, Enum):
    COLLECTION = "collection"
    COURIER_GUY = "courier_guy"

class UserRole(str, Enum):
    CUSTOMER = "customer"
    SELLER = "seller"
    ADMIN = "admin"
```

### Constants

```python
# app/domain/constants.py
from app.domain.enums import CardCondition

# Multiplier applied to market price based on card condition
CONDITION_MULTIPLIERS: dict[CardCondition, float] = {
    CardCondition.MINT: 1.00,
    CardCondition.NEAR_MINT: 0.95,
    CardCondition.LIGHTLY_PLAYED: 0.85,
    CardCondition.MODERATELY_PLAYED: 0.70,
    CardCondition.HEAVILY_PLAYED: 0.50,
    CardCondition.DAMAGED: 0.30,
}

# Shipping
SHIPPING_HANDLING_FEE_ZAR = 25.00   # Added on top of courier quote
MIN_PARCEL_WEIGHT_KG = 0.5          # Courier Guy minimum
DEFAULT_CARD_WEIGHT_GRAMS = 100     # Single card in toploader + mailer
DEFAULT_SEALED_WEIGHT_GRAMS = 500   # Booster box etc.

# Parcel dimensions (cm) — standard card shipping box
DEFAULT_PARCEL_LENGTH = 30
DEFAULT_PARCEL_WIDTH = 20
DEFAULT_PARCEL_HEIGHT = 10

# Order number format
ORDER_NUMBER_PREFIX = "PKM"

# Pagination
DEFAULT_PAGE_SIZE = 24
MAX_PAGE_SIZE = 100
```

### SQLAlchemy Models — Base

```python
# app/domain/models/base.py
from datetime import datetime
import uuid
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass

class UUIDMixin:
    """Adds a UUID primary key."""
    id: Mapped[str] = mapped_column(
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

class TimestampMixin:
    """Adds created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

### SQLAlchemy Models — User

```python
# app/domain/models/user.py
from sqlalchemy import String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.domain.models.base import Base, UUIDMixin, TimestampMixin
from app.domain.enums import UserRole

class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole), default=UserRole.CUSTOMER, nullable=False
    )

    # Saved address
    address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Relationships
    orders: Mapped[list["Order"]] = relationship(back_populates="customer", lazy="selectin")
    cart_items: Mapped[list["CartItem"]] = relationship(back_populates="user", lazy="selectin")
```

### SQLAlchemy Models — Product

```python
# app/domain/models/product.py
from sqlalchemy import String, Float, Integer, Text, Enum as SQLEnum, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.domain.models.base import Base, UUIDMixin, TimestampMixin
from app.domain.enums import ProductType, SealedCategory, CardCondition

class Product(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "products"

    # ── Core (both types) ──
    product_type: Mapped[ProductType] = mapped_column(SQLEnum(ProductType), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    # Values: active | sold_out | delisted

    # ── Sealed product fields ──
    sealed_category: Mapped[SealedCategory | None] = mapped_column(SQLEnum(SealedCategory), nullable=True)
    set_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Human-readable: "Scarlet & Violet — Stellar Crown"

    # ── Single card fields ──
    tcg_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    # pokemontcg.io ID: "sv7-25"
    card_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # "025/198"
    set_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # "sv7"
    rarity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    card_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Element type: "Fire", "Water", etc.
    hp: Mapped[str | None] = mapped_column(String(10), nullable=True)
    artist: Mapped[str | None] = mapped_column(String(100), nullable=True)
    condition: Mapped[CardCondition | None] = mapped_column(SQLEnum(CardCondition), nullable=True)
    condition_multiplier: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Images ──
    tcg_image_small: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Official art from pokemontcg.io
    tcg_image_large: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Seller's actual photo (Cloudinary)
    photo_public_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Cloudinary public_id for deletion

    # ── Pricing ──
    market_price_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    # From pokemontcg.io (singles only)
    market_price_zar: Mapped[float | None] = mapped_column(Float, nullable=True)
    # market_price_usd × exchange_rate
    cost_price_zar: Mapped[float | None] = mapped_column(Float, nullable=True)
    # What the seller paid for this item
    margin_percent: Mapped[float] = mapped_column(Float, default=30.0, nullable=False)
    sell_price_zar: Mapped[float] = mapped_column(Float, nullable=False)
    # Final price the customer pays

    # ── Stock ──
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    quantity_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Weight (for shipping quotes) ──
    weight_grams: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # ── Seller ──
    listed_by: Mapped[str] = mapped_column(String(50), nullable=False)
    # User ID of seller who listed this

    __table_args__ = (
        Index("idx_product_search", "name", "set_name", "product_type", "status"),
        Index("idx_product_type_status", "product_type", "status"),
    )

    @property
    def available_quantity(self) -> int:
        return self.quantity - self.quantity_sold

    @property
    def is_in_stock(self) -> bool:
        return self.available_quantity > 0
```

### SQLAlchemy Models — Order

```python
# app/domain/models/order.py
from sqlalchemy import String, Float, Integer, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.domain.models.base import Base, UUIDMixin, TimestampMixin
from app.domain.enums import OrderStatus, PaymentStatus, ShippingMethod

class Order(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    # PKM-00001 display number
    order_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # Customer (nullable = guest checkout supported)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    # Guest info
    guest_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guest_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guest_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Shipping address (always snapshot on order — never reference user's current address)
    shipping_address_line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shipping_address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    shipping_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipping_province: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipping_postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Shipping details
    shipping_method: Mapped[ShippingMethod] = mapped_column(SQLEnum(ShippingMethod), nullable=False)
    shipping_cost_zar: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    courier_tracking_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    courier_booking_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Totals
    subtotal_zar: Mapped[float] = mapped_column(Float, nullable=False)
    total_zar: Mapped[float] = mapped_column(Float, nullable=False)

    # Status
    order_status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus), default=OrderStatus.PENDING_PAYMENT, nullable=False, index=True
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    payfast_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Notes
    seller_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    customer: Mapped["User | None"] = relationship(back_populates="orders", lazy="selectin")
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", lazy="selectin", cascade="all, delete-orphan"
    )


class OrderItem(UUIDMixin, Base):
    __tablename__ = "order_items"

    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False)

    # Snapshot at time of purchase (never changes even if product is edited later)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_type: Mapped[str] = mapped_column(String(20), nullable=False)
    condition: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_zar: Mapped[float] = mapped_column(Float, nullable=False)
    line_total_zar: Mapped[float] = mapped_column(Float, nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tcg_image_small: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    order: Mapped["Order"] = relationship(back_populates="items")
```

### SQLAlchemy Models — Cart

```python
# app/domain/models/cart.py
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.domain.models.base import Base, UUIDMixin, TimestampMixin

class CartItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cart_items"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="cart_items")
    product: Mapped["Product"] = relationship(lazy="selectin")
```

### SQLAlchemy Models — Exchange Rate

```python
# app/domain/models/exchange_rate.py
from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.domain.models.base import Base, UUIDMixin, TimestampMixin

class ExchangeRate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "exchange_rates"

    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
```

### Models **init** (import all for Alembic)

```python
# app/domain/models/__init__.py
from app.domain.models.base import Base
from app.domain.models.user import User
from app.domain.models.product import Product
from app.domain.models.order import Order, OrderItem
from app.domain.models.cart import CartItem
from app.domain.models.exchange_rate import ExchangeRate

__all__ = ["Base", "User", "Product", "Order", "OrderItem", "CartItem", "ExchangeRate"]
```

---

## PYDANTIC SCHEMAS

### Common

```python
# app/domain/schemas/common.py
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total_count: int
    page: int
    page_size: int
    total_pages: int

class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None

class SuccessResponse(BaseModel):
    message: str
```

### Auth Schemas

```python
# app/domain/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserBriefResponse"

class UserBriefResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str | None
    role: str

    class Config:
        from_attributes = True
```

### User Schemas

```python
# app/domain/schemas/user.py
from pydantic import BaseModel, EmailStr

class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str | None
    role: str
    address_line1: str | None
    address_line2: str | None
    city: str | None
    province: str | None
    postal_code: str | None

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    province: str | None = None
    postal_code: str | None = None
```

### Product Schemas

```python
# app/domain/schemas/product.py
from pydantic import BaseModel, Field
from app.domain.enums import ProductType, SealedCategory, CardCondition

# ── Create Requests ──

class SealedProductCreate(BaseModel):
    """List a new sealed product (booster box, pack, ETB, etc.)."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    sealed_category: SealedCategory
    set_name: str | None = None
    cost_price_zar: float | None = Field(None, ge=0)
    sell_price_zar: float = Field(..., gt=0)
    quantity: int = Field(1, ge=1)
    weight_grams: int = Field(500, ge=1)

class SingleCardCreate(BaseModel):
    """List a single card — system fetches all data from pokemontcg.io via tcg_id."""
    tcg_id: str = Field(..., min_length=1, max_length=50)
    condition: CardCondition
    cost_price_zar: float | None = Field(None, ge=0)
    margin_percent: float = Field(30.0, ge=0, le=200)
    quantity: int = Field(1, ge=1)

class ProductUpdate(BaseModel):
    """Partial update for any product."""
    sell_price_zar: float | None = Field(None, gt=0)
    quantity: int | None = Field(None, ge=0)
    status: str | None = None
    description: str | None = None
    condition: CardCondition | None = None
    margin_percent: float | None = Field(None, ge=0, le=200)

# ── Responses ──

class ProductResponse(BaseModel):
    """Full product detail — used on product detail page."""
    id: str
    product_type: ProductType
    name: str
    description: str | None
    status: str
    sealed_category: SealedCategory | None
    set_name: str | None
    tcg_id: str | None
    card_number: str | None
    set_id: str | None
    rarity: str | None
    card_type: str | None
    hp: str | None
    artist: str | None
    condition: CardCondition | None
    condition_multiplier: float | None
    tcg_image_small: str | None
    tcg_image_large: str | None
    photo_url: str | None
    market_price_usd: float | None
    market_price_zar: float | None
    cost_price_zar: float | None
    margin_percent: float
    sell_price_zar: float
    quantity: int
    quantity_sold: int
    available_quantity: int
    is_in_stock: bool
    weight_grams: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class ProductListResponse(BaseModel):
    """Lightweight response for browse/grid views — fewer fields = faster."""
    id: str
    product_type: ProductType
    name: str
    set_name: str | None
    sealed_category: SealedCategory | None
    condition: CardCondition | None
    rarity: str | None
    tcg_image_small: str | None
    photo_url: str | None
    sell_price_zar: float
    available_quantity: int
    is_in_stock: bool
    created_at: str

    class Config:
        from_attributes = True

class PriceCheckResponse(BaseModel):
    """Returned when seller checks pricing before listing a card."""
    tcg_id: str
    card_name: str
    set_name: str
    rarity: str | None
    tcg_image_small: str | None
    tcg_image_large: str | None
    market_price_usd: float | None
    exchange_rate: float
    market_price_zar: float | None
    condition: str
    condition_multiplier: float
    adjusted_market_zar: float
    margin_percent: float
    sell_price_zar: float
    cost_price_zar: float | None
    profit_zar: float | None

class InventoryStatsResponse(BaseModel):
    """Dashboard stats for seller."""
    total_products_listed: int
    total_in_stock: int
    total_sold: int
    stock_value_zar: float
    total_revenue_zar: float
    total_profit_zar: float
```

### Order Schemas

```python
# app/domain/schemas/order.py
from pydantic import BaseModel
from app.domain.enums import OrderStatus, PaymentStatus, ShippingMethod

class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    product_type: str
    condition: str | None
    quantity: int
    unit_price_zar: float
    line_total_zar: float
    photo_url: str | None
    tcg_image_small: str | None

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: str
    order_number: str
    order_status: OrderStatus
    payment_status: PaymentStatus
    shipping_method: ShippingMethod
    shipping_cost_zar: float
    subtotal_zar: float
    total_zar: float
    courier_tracking_number: str | None
    courier_booking_reference: str | None
    shipping_address_line1: str | None
    shipping_city: str | None
    shipping_province: str | None
    shipping_postal_code: str | None
    guest_email: str | None
    guest_name: str | None
    items: list[OrderItemResponse]
    seller_notes: str | None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class OrderListResponse(BaseModel):
    """Lightweight order for list views."""
    id: str
    order_number: str
    order_status: OrderStatus
    payment_status: PaymentStatus
    total_zar: float
    item_count: int
    shipping_method: ShippingMethod
    created_at: str

    class Config:
        from_attributes = True
```

### Cart Schemas

```python
# app/domain/schemas/cart.py
from pydantic import BaseModel, Field

class CartItemAdd(BaseModel):
    product_id: str
    quantity: int = Field(1, ge=1, le=10)

class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1, le=10)

class CartItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    product_type: str
    condition: str | None
    sell_price_zar: float
    quantity: int
    line_total_zar: float
    tcg_image_small: str | None
    photo_url: str | None
    is_in_stock: bool
    available_quantity: int

class CartResponse(BaseModel):
    items: list[CartItemResponse]
    item_count: int
    subtotal_zar: float
    total_weight_grams: int
```

### Shipping Schemas

```python
# app/domain/schemas/shipping.py
from pydantic import BaseModel, Field

class ShippingQuoteRequest(BaseModel):
    address_line1: str = Field(..., min_length=1)
    city: str = Field(..., min_length=1)
    province: str = Field(..., min_length=1)
    postal_code: str = Field(..., min_length=4, max_length=5)
    total_weight_grams: int | None = None  # Auto-calculated from cart if None

class ShippingQuoteResponse(BaseModel):
    courier_cost_zar: float
    customer_cost_zar: float
    handling_fee_zar: float
    estimated_days: int
    service_name: str

class ShipmentBookRequest(BaseModel):
    order_id: str

class ShipmentBookResponse(BaseModel):
    tracking_number: str
    booking_reference: str
    collection_date: str
    tracking_url: str

class CourierGuyWebhookPayload(BaseModel):
    tracking_number: str
    status: str
    timestamp: str
    description: str | None = None
```

### Checkout Schemas

```python
# app/domain/schemas/checkout.py
from pydantic import BaseModel, EmailStr, Field
from app.domain.enums import ShippingMethod

class CheckoutRequest(BaseModel):
    # Guest info (required if not logged in)
    email: EmailStr | None = None
    full_name: str | None = None
    phone: str | None = None

    # Shipping
    shipping_method: ShippingMethod
    shipping_address_line1: str | None = None
    shipping_address_line2: str | None = None
    shipping_city: str | None = None
    shipping_province: str | None = None
    shipping_postal_code: str | None = None
    shipping_cost_zar: float = 0.0

class CheckoutResponse(BaseModel):
    order: dict  # OrderResponse
    payment_url: str
    payment_data: dict  # Form fields to POST to PayFast
```

---

## UTILITY MODULES

### Security

```python
# app/utils/security.py
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from jose import jwt, JWTError
from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(subject: str, role: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
```

### Pagination

```python
# app/utils/pagination.py
import math
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.schemas.common import PaginatedResponse

async def paginate(
    db: AsyncSession,
    query,
    page: int,
    page_size: int,
    response_model=None,
) -> PaginatedResponse:
    """Generic pagination helper for any SQLAlchemy query."""
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    paginated_query = query.offset(offset).limit(page_size)
    result = await db.execute(paginated_query)
    items = result.scalars().all()

    # Convert to response model if provided
    if response_model:
        items = [response_model.model_validate(item) for item in items]

    return PaginatedResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total_count / page_size) if page_size > 0 else 0,
    )
```

### Custom Exceptions

```python
# app/utils/exceptions.py

class AppException(Exception):
    """Base application exception."""
    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: str = ""):
        super().__init__(f"{resource} not found: {identifier}", "NOT_FOUND")

class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR")

class AuthorizationError(AppException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, "FORBIDDEN")

class ValidationError(AppException):
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")

class ExternalServiceError(AppException):
    def __init__(self, service: str, message: str):
        super().__init__(f"{service}: {message}", "EXTERNAL_SERVICE_ERROR")

class InsufficientStockError(AppException):
    def __init__(self, product_name: str, available: int, requested: int):
        super().__init__(
            f"Insufficient stock for '{product_name}': {available} available, {requested} requested",
            "INSUFFICIENT_STOCK",
        )
```

---

## REPOSITORY LAYER

### Base Repository

```python
# app/repositories/base.py
from typing import TypeVar, Generic, Type
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

class BaseRepository(Generic[T]):
    """Generic repository with standard CRUD operations."""

    def __init__(self, db: AsyncSession, model: Type[T]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: str) -> T | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        result = await self.db.execute(
            select(self.model).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, entity: T) -> T:
        self.db.add(entity)
        await self.db.flush()
        await self.db.refresh(entity)
        return entity

    async def update_by_id(self, id: str, values: dict) -> T | None:
        await self.db.execute(
            update(self.model).where(self.model.id == id).values(**values)
        )
        await self.db.flush()
        return await self.get_by_id(id)

    async def delete_by_id(self, id: str) -> None:
        await self.db.execute(delete(self.model).where(self.model.id == id))
        await self.db.flush()
```

### Product Repository

```python
# app/repositories/product_repo.py
from sqlalchemy import select, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.domain.models.product import Product
from app.domain.enums import ProductType, CardCondition

class ProductRepository(BaseRepository[Product]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Product)

    async def browse(
        self,
        q: str | None = None,
        product_type: ProductType | None = None,
        sealed_category: str | None = None,
        set_name: str | None = None,
        rarity: str | None = None,
        condition: CardCondition | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        sort: str = "newest",
    ):
        """Build a filtered query for the public store browse endpoint."""
        query = select(Product).where(Product.status == "active")

        if q:
            search = f"%{q}%"
            query = query.where(
                or_(
                    Product.name.ilike(search),
                    Product.set_name.ilike(search),
                    Product.rarity.ilike(search),
                )
            )
        if product_type:
            query = query.where(Product.product_type == product_type)
        if sealed_category:
            query = query.where(Product.sealed_category == sealed_category)
        if set_name:
            query = query.where(Product.set_name.ilike(f"%{set_name}%"))
        if rarity:
            query = query.where(Product.rarity == rarity)
        if condition:
            query = query.where(Product.condition == condition)
        if min_price is not None:
            query = query.where(Product.sell_price_zar >= min_price)
        if max_price is not None:
            query = query.where(Product.sell_price_zar <= max_price)

        # Sorting
        sort_map = {
            "newest": Product.created_at.desc(),
            "price_asc": Product.sell_price_zar.asc(),
            "price_desc": Product.sell_price_zar.desc(),
            "name_asc": Product.name.asc(),
        }
        query = query.order_by(sort_map.get(sort, Product.created_at.desc()))
        return query

    async def get_featured(self, limit: int = 8) -> list[Product]:
        result = await self.db.execute(
            select(Product)
            .where(Product.status == "active")
            .order_by(Product.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_seller(self, seller_id: str, q: str | None = None, status: str | None = None):
        """Build inventory query for seller dashboard."""
        query = select(Product).where(Product.listed_by == seller_id)
        if q:
            query = query.where(Product.name.ilike(f"%{q}%"))
        if status:
            query = query.where(Product.status == status)
        return query.order_by(Product.created_at.desc())

    async def get_inventory_stats(self, seller_id: str) -> dict:
        """Aggregate stats for seller dashboard."""
        base = select(Product).where(Product.listed_by == seller_id)

        total_listed = await self.db.scalar(
            select(func.count()).select_from(base.subquery())
        ) or 0

        in_stock = await self.db.scalar(
            select(func.count()).select_from(
                base.where(Product.status == "active").subquery()
            )
        ) or 0

        total_sold = await self.db.scalar(
            select(func.coalesce(func.sum(Product.quantity_sold), 0))
            .where(Product.listed_by == seller_id)
        ) or 0

        stock_value = await self.db.scalar(
            select(func.coalesce(
                func.sum(Product.sell_price_zar * (Product.quantity - Product.quantity_sold)), 0
            )).where(Product.listed_by == seller_id, Product.status == "active")
        ) or 0.0

        revenue = await self.db.scalar(
            select(func.coalesce(
                func.sum(Product.sell_price_zar * Product.quantity_sold), 0
            )).where(Product.listed_by == seller_id)
        ) or 0.0

        profit = await self.db.scalar(
            select(func.coalesce(
                func.sum(
                    (Product.sell_price_zar - func.coalesce(Product.cost_price_zar, 0)) * Product.quantity_sold
                ), 0
            )).where(Product.listed_by == seller_id)
        ) or 0.0

        return {
            "total_products_listed": total_listed,
            "total_in_stock": in_stock,
            "total_sold": total_sold,
            "stock_value_zar": round(float(stock_value), 2),
            "total_revenue_zar": round(float(revenue), 2),
            "total_profit_zar": round(float(profit), 2),
        }

    async def reduce_stock(self, product_id: str, quantity: int) -> None:
        """Atomically reduce stock after purchase."""
        await self.db.execute(
            update(Product)
            .where(Product.id == product_id)
            .values(quantity_sold=Product.quantity_sold + quantity)
        )
        await self.db.flush()
```

### Order Repository

```python
# app/repositories/order_repo.py
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.repositories.base import BaseRepository
from app.domain.models.order import Order, OrderItem
from app.domain.enums import OrderStatus

class OrderRepository(BaseRepository[Order]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Order)

    async def get_by_id_with_items(self, id: str) -> Order | None:
        result = await self.db.execute(
            select(Order).options(selectinload(Order.items)).where(Order.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_order_number(self, order_number: str) -> Order | None:
        result = await self.db.execute(
            select(Order).options(selectinload(Order.items)).where(Order.order_number == order_number)
        )
        return result.scalar_one_or_none()

    async def get_by_tracking_number(self, tracking_number: str) -> Order | None:
        result = await self.db.execute(
            select(Order).where(Order.courier_tracking_number == tracking_number)
        )
        return result.scalar_one_or_none()

    async def get_customer_orders(self, customer_id: str):
        return (
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc())
        )

    async def get_all_orders(self, status: OrderStatus | None = None):
        query = select(Order).options(selectinload(Order.items))
        if status:
            query = query.where(Order.order_status == status)
        return query.order_by(Order.created_at.desc())

    async def get_next_order_number(self) -> str:
        count = await self.db.scalar(select(func.count()).select_from(Order)) or 0
        return f"PKM-{(count + 1):05d}"
```

### Cart Repository

```python
# app/repositories/cart_repo.py
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.repositories.base import BaseRepository
from app.domain.models.cart import CartItem

class CartRepository(BaseRepository[CartItem]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, CartItem)

    async def get_user_cart(self, user_id: str) -> list[CartItem]:
        result = await self.db.execute(
            select(CartItem)
            .options(selectinload(CartItem.product))
            .where(CartItem.user_id == user_id)
            .order_by(CartItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_user_cart_item(self, user_id: str, product_id: str) -> CartItem | None:
        result = await self.db.execute(
            select(CartItem).where(
                CartItem.user_id == user_id,
                CartItem.product_id == product_id,
            )
        )
        return result.scalar_one_or_none()

    async def clear_user_cart(self, user_id: str) -> None:
        await self.db.execute(delete(CartItem).where(CartItem.user_id == user_id))
        await self.db.flush()
```

### User Repository

```python
# app/repositories/user_repo.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.domain.models.user import User

class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, User)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
```

### Exchange Rate Repository

```python
# app/repositories/exchange_rate_repo.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base import BaseRepository
from app.domain.models.exchange_rate import ExchangeRate

class ExchangeRateRepository(BaseRepository[ExchangeRate]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, ExchangeRate)

    async def get_latest(self, from_currency: str, to_currency: str) -> ExchangeRate | None:
        result = await self.db.execute(
            select(ExchangeRate)
            .where(
                ExchangeRate.from_currency == from_currency,
                ExchangeRate.to_currency == to_currency,
            )
            .order_by(ExchangeRate.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
```

---

## EXTERNAL API CLIENTS

### Pokemon TCG Client

```python
# app/clients/pokemon_tcg_client.py
"""
pokemontcg.io v2 API wrapper.
Docs: https://docs.pokemontcg.io/
Rate limit: 20,000/day with API key, 1,000 without.
"""
import httpx
from cachetools import TTLCache
from app.config import get_settings

class PokemonTCGClient:
    BASE_URL = "https://api.pokemontcg.io/v2"

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.pokemon_tcg_api_key
        self.headers = {"X-Api-Key": self.api_key} if self.api_key else {}
        self._card_cache = TTLCache(maxsize=500, ttl=900)   # 15 min
        self._set_cache = TTLCache(maxsize=100, ttl=3600)    # 1 hour

    async def get_card(self, tcg_id: str) -> dict | None:
        """Fetch card by pokemontcg.io ID (e.g. 'sv7-25')."""
        if tcg_id in self._card_cache:
            return self._card_cache[tcg_id]

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/cards/{tcg_id}", headers=self.headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()["data"]
                self._card_cache[tcg_id] = data
                return data
        return None

    async def search_cards(self, query: str, page: int = 1, page_size: int = 20) -> dict:
        """Search cards by name. Returns { data, totalCount, page, pageSize }."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/cards",
                params={"q": f"name:{query}*", "page": page, "pageSize": page_size, "orderBy": "-set.releaseDate"},
                headers=self.headers, timeout=10.0,
            )
            if resp.status_code == 200:
                return resp.json()
        return {"data": [], "totalCount": 0}

    async def get_sets(self) -> list[dict]:
        """Get all Pokemon TCG sets, newest first."""
        if "all_sets" in self._set_cache:
            return self._set_cache["all_sets"]

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/sets", params={"orderBy": "-releaseDate"}, headers=self.headers, timeout=10.0)
            if resp.status_code == 200:
                sets = resp.json()["data"]
                self._set_cache["all_sets"] = sets
                return sets
        return []

    def extract_market_price(self, card_data: dict) -> float | None:
        """Extract best market price from TCGPlayer data. Returns USD or None."""
        prices = card_data.get("tcgplayer", {}).get("prices", {})
        for variant in ["holofoil", "normal", "reverseHolofoil", "1stEditionHolofoil"]:
            for key in ["market", "mid", "low"]:
                price = prices.get(variant, {}).get(key)
                if price and price > 0:
                    return price
        return None
```

### PayFast Client

```python
# app/clients/payfast_client.py
"""
PayFast payment gateway.
Docs: https://developers.payfast.co.za/docs

Flow:
1. Generate signed payment data → frontend POSTs a form to PayFast
2. Customer pays on PayFast's hosted page
3. PayFast sends ITN (webhook) to /api/v1/checkout/payfast/notify
4. We verify signature + server validation → update order
"""
import hashlib
import urllib.parse
import httpx
from app.config import get_settings

class PayFastClient:
    SANDBOX_PROCESS = "https://sandbox.payfast.co.za/eng/process"
    PRODUCTION_PROCESS = "https://www.payfast.co.za/eng/process"
    SANDBOX_VALIDATE = "https://sandbox.payfast.co.za/eng/query/validate"
    PRODUCTION_VALIDATE = "https://www.payfast.co.za/eng/query/validate"

    def __init__(self):
        settings = get_settings()
        self.merchant_id = settings.payfast_merchant_id
        self.merchant_key = settings.payfast_merchant_key
        self.passphrase = settings.payfast_passphrase
        self.is_sandbox = settings.payfast_sandbox
        self.return_url = settings.payfast_return_url
        self.cancel_url = settings.payfast_cancel_url
        self.notify_url = settings.payfast_notify_url

    @property
    def process_url(self) -> str:
        return self.SANDBOX_PROCESS if self.is_sandbox else self.PRODUCTION_PROCESS

    @property
    def validate_url(self) -> str:
        return self.SANDBOX_VALIDATE if self.is_sandbox else self.PRODUCTION_VALIDATE

    def generate_payment_data(
        self, order_number: str, total_zar: float, item_name: str,
        email: str, name_first: str = "", name_last: str = "",
    ) -> dict:
        """Build signed payment form data. Frontend submits this as a POST form to PayFast."""
        data = {
            "merchant_id": self.merchant_id,
            "merchant_key": self.merchant_key,
            "return_url": f"{self.return_url}?order={order_number}",
            "cancel_url": self.cancel_url,
            "notify_url": self.notify_url,
            "name_first": name_first,
            "name_last": name_last,
            "email_address": email,
            "m_payment_id": order_number,
            "amount": f"{total_zar:.2f}",
            "item_name": item_name[:100],
        }
        data = {k: v for k, v in data.items() if v}
        data["signature"] = self._sign(data)
        return data

    def _sign(self, data: dict) -> str:
        param_str = "&".join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in data.items() if v and k != "signature")
        if self.passphrase:
            param_str += f"&passphrase={urllib.parse.quote_plus(self.passphrase)}"
        return hashlib.md5(param_str.encode()).hexdigest()

    def verify_itn_signature(self, posted: dict) -> bool:
        received = posted.get("signature", "")
        clean = {k: v for k, v in posted.items() if k != "signature" and v}
        param_str = "&".join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in clean.items())
        if self.passphrase:
            param_str += f"&passphrase={urllib.parse.quote_plus(self.passphrase)}"
        return hashlib.md5(param_str.encode()).hexdigest() == received

    async def validate_itn_server(self, posted: dict) -> bool:
        """Server-to-server validation — confirm ITN is legit."""
        param_str = "&".join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in posted.items())
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.validate_url, data=param_str,
                                     headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30.0)
            return resp.text.strip() == "VALID"
```

### Courier Guy Client

```python
# app/clients/courier_guy_client.py
"""
The Courier Guy API.
Docs: https://developer.thecourierguy.co.za/

Flow:
1. Get quote → customer sees live shipping price at checkout
2. Book shipment → Courier Guy collects from YOUR address, delivers to customer
3. Webhook → status updates (collected, in_transit, out_for_delivery, delivered)
4. Customer gets WhatsApp tracking from Courier Guy automatically
"""
import httpx
import hmac
import hashlib
from app.config import get_settings
from app.domain.constants import (
    MIN_PARCEL_WEIGHT_KG, DEFAULT_PARCEL_LENGTH,
    DEFAULT_PARCEL_WIDTH, DEFAULT_PARCEL_HEIGHT,
)

class CourierGuyClient:
    BASE_URL = "https://api.thecourierguy.co.za/v2"

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.courier_guy_api_key
        self.account_number = settings.courier_guy_account_number
        self.webhook_secret = settings.courier_guy_webhook_secret
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        self.seller_address = {
            "street_address": settings.seller_address_line1,
            "city": settings.seller_city,
            "province": settings.seller_province,
            "postal_code": settings.seller_postal_code,
            "contact_name": "Pokemon Cards SA",
            "contact_phone": settings.seller_phone,
            "type": "business",
        }

    async def get_quote(
        self, destination_address: str, destination_city: str,
        destination_province: str, destination_postal_code: str,
        total_weight_kg: float, parcels: int = 1,
    ) -> dict | None:
        """Get cheapest shipping rate."""
        payload = {
            "collection_address": self.seller_address,
            "delivery_address": {
                "street_address": destination_address, "city": destination_city,
                "province": destination_province, "postal_code": destination_postal_code,
                "type": "residential",
            },
            "parcels": [{
                "weight": max(total_weight_kg, MIN_PARCEL_WEIGHT_KG),
                "length": DEFAULT_PARCEL_LENGTH, "width": DEFAULT_PARCEL_WIDTH,
                "height": DEFAULT_PARCEL_HEIGHT,
            } for _ in range(parcels)],
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.BASE_URL}/rates", json=payload, headers=self.headers, timeout=15.0)
            if resp.status_code == 200:
                rates = resp.json().get("rates", [])
                if rates:
                    cheapest = min(rates, key=lambda r: r.get("rate", float("inf")))
                    return {
                        "service_type": cheapest.get("service_type", "standard"),
                        "rate_zar": float(cheapest.get("rate", 0)),
                        "estimated_days": int(cheapest.get("estimated_delivery_days", 3)),
                        "service_name": cheapest.get("service_name", "Standard"),
                    }
        return None

    async def book_shipment(
        self, order_number: str, destination_address: str, destination_city: str,
        destination_province: str, destination_postal_code: str,
        destination_contact_name: str, destination_contact_phone: str,
        destination_contact_email: str, total_weight_kg: float,
        description: str = "Pokemon Trading Cards",
    ) -> dict | None:
        """Book collection from seller + delivery to customer. Returns tracking info."""
        payload = {
            "account_number": self.account_number,
            "collection_address": self.seller_address,
            "delivery_address": {
                "street_address": destination_address, "city": destination_city,
                "province": destination_province, "postal_code": destination_postal_code,
                "contact_name": destination_contact_name, "contact_phone": destination_contact_phone,
                "contact_email": destination_contact_email, "type": "residential",
            },
            "parcels": [{
                "weight": max(total_weight_kg, MIN_PARCEL_WEIGHT_KG),
                "length": DEFAULT_PARCEL_LENGTH, "width": DEFAULT_PARCEL_WIDTH,
                "height": DEFAULT_PARCEL_HEIGHT, "description": description,
            }],
            "special_instructions": f"Order {order_number} — Handle with care",
            "reference": order_number,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.BASE_URL}/shipments", json=payload, headers=self.headers, timeout=15.0)
            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "tracking_number": data.get("tracking_number"),
                    "booking_reference": data.get("reference"),
                    "collection_date": data.get("estimated_collection_date"),
                    "tracking_url": f"https://tracking.thecourierguy.co.za/{data.get('tracking_number', '')}",
                }
        return None

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        if not self.webhook_secret:
            return True
        expected = hmac.new(self.webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
```

### Cloudinary Client

```python
# app/clients/cloudinary_client.py
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile
from app.config import get_settings

class CloudinaryClient:
    def __init__(self):
        settings = get_settings()
        cloudinary.config(
            cloud_name=settings.cloudinary_cloud_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret,
        )

    async def upload_image(self, file: UploadFile, folder: str = "pokemon-store") -> dict:
        contents = await file.read()
        result = cloudinary.uploader.upload(
            contents, folder=folder, resource_type="image",
            transformation=[{"quality": "auto:good", "fetch_format": "auto"}, {"width": 1200, "crop": "limit"}],
        )
        return {"url": result["secure_url"], "public_id": result["public_id"],
                "width": result["width"], "height": result["height"]}

    async def delete_image(self, public_id: str) -> bool:
        result = cloudinary.uploader.destroy(public_id)
        return result.get("result") == "ok"
```

---

## SERVICE LAYER

### Auth Service

```python
# app/services/auth_service.py
from app.repositories.user_repo import UserRepository
from app.domain.models.user import User
from app.domain.enums import UserRole
from app.domain.schemas.auth import RegisterRequest, TokenResponse, UserBriefResponse
from app.utils.security import hash_password, verify_password, create_access_token

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register(self, data: RegisterRequest) -> TokenResponse:
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise ValueError("Email already registered")

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            phone=data.phone,
            role=UserRole.CUSTOMER,
        )
        user = await self.user_repo.create(user)
        token = create_access_token(user.id, user.role.value)

        return TokenResponse(
            access_token=token,
            user=UserBriefResponse.model_validate(user),
        )

    async def login(self, email: str, password: str) -> TokenResponse | None:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            return None

        token = create_access_token(user.id, user.role.value)
        return TokenResponse(
            access_token=token,
            user=UserBriefResponse.model_validate(user),
        )
```

### Pricing Service

```python
# app/services/pricing_service.py
from app.clients.pokemon_tcg_client import PokemonTCGClient
from app.repositories.exchange_rate_repo import ExchangeRateRepository
from app.domain.enums import CardCondition
from app.domain.constants import CONDITION_MULTIPLIERS, SHIPPING_HANDLING_FEE_ZAR
from app.config import get_settings

class PricingService:
    def __init__(self, pokemon_client: PokemonTCGClient, exchange_rate_repo: ExchangeRateRepository):
        self.pokemon_client = pokemon_client
        self.exchange_rate_repo = exchange_rate_repo

    async def get_exchange_rate(self) -> float:
        rate = await self.exchange_rate_repo.get_latest("USD", "ZAR")
        return rate.rate if rate else get_settings().usd_to_zar_default

    async def get_card_pricing(
        self, tcg_id: str, condition: CardCondition,
        margin_percent: float = 30.0, cost_price_zar: float | None = None,
    ) -> dict:
        """Full pricing breakdown for a single card."""
        card_data = await self.pokemon_client.get_card(tcg_id)
        if not card_data:
            raise ValueError(f"Card not found: {tcg_id}")

        market_usd = self.pokemon_client.extract_market_price(card_data)
        exchange_rate = await self.get_exchange_rate()
        multiplier = CONDITION_MULTIPLIERS.get(condition, 0.95)

        market_zar = (market_usd or 0) * exchange_rate
        adjusted_zar = market_zar * multiplier
        sell_price_zar = adjusted_zar * (1 + margin_percent / 100)

        return {
            "card_data": card_data,
            "market_price_usd": market_usd,
            "market_price_zar": round(market_zar, 2),
            "condition_multiplier": multiplier,
            "adjusted_market_zar": round(adjusted_zar, 2),
            "sell_price_zar": round(sell_price_zar, 2),
            "profit_zar": round(sell_price_zar - (cost_price_zar or 0), 2),
            "exchange_rate": exchange_rate,
        }

    def calculate_sealed_margin(self, cost: float, sell: float) -> float:
        if cost <= 0:
            return 0.0
        return round(((sell - cost) / cost) * 100, 1)

    def calculate_shipping_customer_price(self, courier_quote_zar: float) -> dict:
        customer_price = courier_quote_zar + SHIPPING_HANDLING_FEE_ZAR
        return {
            "courier_cost_zar": round(courier_quote_zar, 2),
            "customer_cost_zar": round(customer_price, 2),
            "handling_fee_zar": SHIPPING_HANDLING_FEE_ZAR,
        }
```

### Shipping Service

```python
# app/services/shipping_service.py
from app.clients.courier_guy_client import CourierGuyClient
from app.repositories.order_repo import OrderRepository
from app.services.pricing_service import PricingService
from app.domain.enums import OrderStatus

class ShippingService:
    def __init__(self, courier_client: CourierGuyClient, order_repo: OrderRepository, pricing_service: PricingService):
        self.courier_client = courier_client
        self.order_repo = order_repo
        self.pricing_service = pricing_service

    async def get_quote(self, address: str, city: str, province: str, postal_code: str, total_weight_grams: int) -> dict:
        weight_kg = max(total_weight_grams / 1000, 0.5)
        quote = await self.courier_client.get_quote(address, city, province, postal_code, weight_kg)
        if not quote:
            raise ValueError("Could not get shipping quote. Please check the address.")
        pricing = self.pricing_service.calculate_shipping_customer_price(quote["rate_zar"])
        return {**pricing, "estimated_days": quote["estimated_days"], "service_name": quote["service_name"]}

    async def book_shipment(self, order_id: str) -> dict:
        order = await self.order_repo.get_by_id_with_items(order_id)
        if not order:
            raise ValueError("Order not found")
        if order.order_status not in (OrderStatus.PAID, OrderStatus.CONFIRMED):
            raise ValueError(f"Cannot ship order in status: {order.order_status}")

        total_weight_kg = sum((item.quantity * 100) / 1000 for item in order.items)
        customer_name = order.guest_name or (order.customer.full_name if order.customer else "Customer")
        customer_phone = order.guest_phone or (order.customer.phone if order.customer else "")
        customer_email = order.guest_email or (order.customer.email if order.customer else "")

        result = await self.courier_client.book_shipment(
            order_number=order.order_number,
            destination_address=order.shipping_address_line1 or "",
            destination_city=order.shipping_city or "",
            destination_province=order.shipping_province or "",
            destination_postal_code=order.shipping_postal_code or "",
            destination_contact_name=customer_name,
            destination_contact_phone=customer_phone,
            destination_contact_email=customer_email,
            total_weight_kg=total_weight_kg,
        )
        if not result:
            raise ValueError("Failed to book shipment with Courier Guy")

        await self.order_repo.update_by_id(order_id, {
            "courier_tracking_number": result["tracking_number"],
            "courier_booking_reference": result["booking_reference"],
            "order_status": OrderStatus.SHIPPED,
        })
        return result

    async def handle_webhook(self, tracking_number: str, status: str) -> None:
        status_map = {
            "collected": OrderStatus.SHIPPED,
            "in_transit": OrderStatus.IN_TRANSIT,
            "out_for_delivery": OrderStatus.OUT_FOR_DELIVERY,
            "delivered": OrderStatus.DELIVERED,
        }
        new_status = status_map.get(status.lower())
        if not new_status:
            return
        order = await self.order_repo.get_by_tracking_number(tracking_number)
        if order:
            await self.order_repo.update_by_id(order.id, {"order_status": new_status})
```

### Payment Service

```python
# app/services/payment_service.py
from app.clients.payfast_client import PayFastClient
from app.repositories.order_repo import OrderRepository
from app.repositories.product_repo import ProductRepository
from app.services.shipping_service import ShippingService
from app.domain.enums import OrderStatus, PaymentStatus, ShippingMethod
from fastapi import BackgroundTasks

class PaymentService:
    def __init__(self, payfast_client: PayFastClient, order_repo: OrderRepository,
                 product_repo: ProductRepository, shipping_service: ShippingService):
        self.payfast = payfast_client
        self.order_repo = order_repo
        self.product_repo = product_repo
        self.shipping_service = shipping_service

    def generate_checkout(self, order) -> dict:
        item_count = sum(item.quantity for item in order.items)
        email = order.guest_email or (order.customer.email if order.customer else "")
        name = order.guest_name or (order.customer.full_name if order.customer else "")
        parts = name.split(" ", 1)

        payment_data = self.payfast.generate_payment_data(
            order_number=order.order_number, total_zar=order.total_zar,
            item_name=f"Pokemon Cards SA — {item_count} item(s)", email=email,
            name_first=parts[0] if parts else "", name_last=parts[1] if len(parts) > 1 else "",
        )
        return {"payment_url": self.payfast.process_url, "payment_data": payment_data}

    async def handle_itn(self, posted_data: dict, background_tasks: BackgroundTasks) -> bool:
        # 1. Verify signature
        if not self.payfast.verify_itn_signature(posted_data):
            return False

        # 2. Server validation
        if not await self.payfast.validate_itn_server(posted_data):
            return False

        # 3. Find order
        order_number = posted_data.get("m_payment_id")
        order = await self.order_repo.get_by_order_number(order_number)
        if not order:
            return False

        # 4. Verify amount
        received = float(posted_data.get("amount_gross", 0))
        if abs(received - order.total_zar) > 0.01:
            return False

        status = posted_data.get("payment_status", "")

        if status == "COMPLETE":
            await self.order_repo.update_by_id(order.id, {
                "payment_status": PaymentStatus.COMPLETE,
                "order_status": OrderStatus.PAID,
                "payfast_payment_id": posted_data.get("pf_payment_id"),
            })

            # Background: reduce stock
            background_tasks.add_task(self._reduce_stock, order)

            # Background: auto-book courier if selected
            if order.shipping_method == ShippingMethod.COURIER_GUY:
                background_tasks.add_task(self._auto_book_shipping, order.id)

            return True

        elif status == "CANCELLED":
            await self.order_repo.update_by_id(order.id, {
                "payment_status": PaymentStatus.CANCELLED,
                "order_status": OrderStatus.CANCELLED,
            })
            return True

        return False

    async def _reduce_stock(self, order) -> None:
        for item in order.items:
            await self.product_repo.reduce_stock(item.product_id, item.quantity)

    async def _auto_book_shipping(self, order_id: str) -> None:
        try:
            await self.shipping_service.book_shipment(order_id)
        except Exception as e:
            print(f"⚠️ Auto-ship failed for {order_id}: {e}")
```

### Image Service

```python
# app/services/image_service.py
from fastapi import UploadFile
from app.clients.cloudinary_client import CloudinaryClient

class ImageService:
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
    MAX_SIZE_MB = 10

    def __init__(self, cloudinary_client: CloudinaryClient):
        self.cloudinary = cloudinary_client

    async def upload_product_photo(self, file: UploadFile, product_id: str) -> dict:
        if file.content_type not in self.ALLOWED_TYPES:
            raise ValueError(f"File type not allowed: {file.content_type}. Use JPEG, PNG, or WebP.")
        return await self.cloudinary.upload_image(file, folder=f"pokemon-store/{product_id}")

    async def delete_product_photo(self, public_id: str) -> bool:
        return await self.cloudinary.delete_image(public_id)
```

---

## API ROUTES

### Auth

```python
# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException
from app.domain.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.services.auth_service import AuthService
from app.api.deps import get_auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: RegisterRequest, service: AuthService = Depends(get_auth_service)):
    try:
        return await service.register(data)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, service: AuthService = Depends(get_auth_service)):
    result = await service.login(data.email, data.password)
    if not result:
        raise HTTPException(401, "Invalid email or password")
    return result
```

### Users

```python
# app/api/v1/users.py
from fastapi import APIRouter, Depends
from app.domain.schemas.user import UserProfileResponse, UserProfileUpdate
from app.domain.models.user import User
from app.repositories.user_repo import UserRepository
from app.api.deps import get_current_user
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserProfileResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user

@router.put("/me", response_model=UserProfileResponse)
async def update_me(
    data: UserProfileUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    updated = await repo.update_by_id(user.id, data.model_dump(exclude_unset=True))
    return updated
```

### Store (Public)

```python
# app/api/v1/store.py
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
```

### Products (Seller)

```python
# app/api/v1/products.py
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
```

### Cart

```python
# app/api/v1/cart.py
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
```

### Checkout

```python
# app/api/v1/checkout.py
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from app.domain.schemas.checkout import CheckoutRequest
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService
from app.api.deps import get_order_service, get_payment_service, get_current_user_optional
from app.domain.models.user import User

router = APIRouter(prefix="/checkout", tags=["Checkout"])

@router.post("/create-order")
async def create_order(data: CheckoutRequest, user: User | None = Depends(get_current_user_optional),
                       order_service: OrderService = Depends(get_order_service),
                       payment_service: PaymentService = Depends(get_payment_service)):
    try:
        order = await order_service.create_from_cart(user, data)
        checkout = payment_service.generate_checkout(order)
        return {"order": order, **checkout}
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/payfast/notify")
async def payfast_itn(request: Request, background_tasks: BackgroundTasks,
                      payment_service: PaymentService = Depends(get_payment_service)):
    """PayFast Instant Transaction Notification webhook."""
    form = await request.form()
    success = await payment_service.handle_itn(dict(form), background_tasks)
    if not success:
        raise HTTPException(400, "ITN validation failed")
    return {"status": "ok"}
```

### Orders

```python
# app/api/v1/orders.py
from fastapi import APIRouter, Depends, Query, HTTPException
from app.services.order_service import OrderService
from app.api.deps import get_order_service, get_current_user, require_seller
from app.domain.models.user import User
from app.domain.enums import OrderStatus

router = APIRouter(prefix="/orders", tags=["Orders"])

# Customer
@router.get("/my")
async def my_orders(page: int = Query(1, ge=1), user: User = Depends(get_current_user),
                    service: OrderService = Depends(get_order_service)):
    return await service.get_customer_orders(user.id, page)

@router.get("/my/{order_number}")
async def my_order(order_number: str, user: User = Depends(get_current_user),
                   service: OrderService = Depends(get_order_service)):
    order = await service.get_by_order_number(order_number)
    if not order or order.customer_id != user.id:
        raise HTTPException(404, "Order not found")
    return order

# Guest tracking
@router.get("/track/{order_number}")
async def track(order_number: str, email: str = Query(...),
                service: OrderService = Depends(get_order_service)):
    order = await service.get_by_order_number(order_number)
    if not order or (order.guest_email != email and (not order.customer or order.customer.email != email)):
        raise HTTPException(404, "Order not found")
    return order

# Seller
@router.get("/manage")
async def all_orders(status: OrderStatus | None = None, page: int = Query(1, ge=1),
                     user: User = Depends(require_seller),
                     service: OrderService = Depends(get_order_service)):
    return await service.get_all_orders(status, page)

@router.put("/manage/{order_id}/status")
async def update_status(order_id: str, status: OrderStatus,
                        user: User = Depends(require_seller),
                        service: OrderService = Depends(get_order_service)):
    return await service.update_status(order_id, status)

@router.put("/manage/{order_id}/tracking")
async def add_tracking(order_id: str, tracking_number: str,
                       user: User = Depends(require_seller),
                       service: OrderService = Depends(get_order_service)):
    return await service.add_tracking(order_id, tracking_number)
```

### Shipping

```python
# app/api/v1/shipping.py
from fastapi import APIRouter, Depends, HTTPException, Request
from app.domain.schemas.shipping import ShippingQuoteRequest, ShippingQuoteResponse, ShipmentBookRequest, ShipmentBookResponse
from app.services.shipping_service import ShippingService
from app.api.deps import get_shipping_service, require_seller

router = APIRouter(prefix="/shipping", tags=["Shipping"])

@router.post("/quote", response_model=ShippingQuoteResponse)
async def quote(data: ShippingQuoteRequest, service: ShippingService = Depends(get_shipping_service)):
    """Live shipping quote from Courier Guy. Customer calls this at checkout."""
    try:
        return await service.get_quote(data.address_line1, data.city, data.province, data.postal_code,
                                        data.total_weight_grams or 500)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/book", response_model=ShipmentBookResponse)
async def book(data: ShipmentBookRequest, user=Depends(require_seller),
               service: ShippingService = Depends(get_shipping_service)):
    """Book Courier Guy collection. Can also be auto-triggered after payment."""
    try:
        return await service.book_shipment(data.order_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.post("/webhook/courier-guy")
async def courier_webhook(request: Request, service: ShippingService = Depends(get_shipping_service)):
    """Courier Guy calls this when status changes. Updates order automatically."""
    body = await request.body()
    sig = request.headers.get("X-Signature", "")
    if not service.courier_client.verify_webhook(body, sig):
        raise HTTPException(403, "Invalid webhook signature")
    data = await request.json()
    await service.handle_webhook(data.get("tracking_number", ""), data.get("status", ""))
    return {"status": "ok"}
```

### Admin

```python
# app/api/v1/admin.py
from fastapi import APIRouter, Depends
from app.api.deps import require_seller
from app.repositories.exchange_rate_repo import ExchangeRateRepository
from app.domain.models.exchange_rate import ExchangeRate
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["Admin"])

class ExchangeRateUpdate(BaseModel):
    rate: float

@router.get("/exchange-rate")
async def get_rate(user=Depends(require_seller), db: AsyncSession = Depends(get_db)):
    repo = ExchangeRateRepository(db)
    rate = await repo.get_latest("USD", "ZAR")
    return {"rate": rate.rate if rate else 18.50, "source": rate.source if rate else "default"}

@router.put("/exchange-rate")
async def set_rate(data: ExchangeRateUpdate, user=Depends(require_seller), db: AsyncSession = Depends(get_db)):
    repo = ExchangeRateRepository(db)
    rate = ExchangeRate(from_currency="USD", to_currency="ZAR", rate=data.rate, source="manual")
    await repo.create(rate)
    return {"rate": data.rate, "source": "manual"}
```

---

## DEPENDENCY INJECTION WIRING

```python
# app/api/deps.py
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
```

---

## MAIN APP

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import get_settings
from app.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Pokemon Card Store API starting...")
    yield
    print("👋 Shutting down...")

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Pokemon Card Store API",
        description="South African Pokemon card reselling platform",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "pokemon-card-store-api"}

    return app

app = create_app()
```

```python
# app/api/router.py
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
```

---

## DEPLOYMENT

### requirements.txt

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy[asyncio]==2.0.35
asyncpg==0.30.0
alembic==1.13.0
pydantic==2.9.0
pydantic-settings==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
httpx==0.27.0
cachetools==5.5.0
cloudinary==1.41.0
email-validator==2.2.0
ruff==0.6.0
pytest==8.3.0
pytest-asyncio==0.24.0
```

### Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### render.yaml

```yaml
services:
  - type: web
    name: pokemon-api
    runtime: python
    buildCommand: pip install -r requirements.txt && alembic upgrade head
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: JWT_SECRET_KEY
        generateValue: true
      - key: PAYFAST_MERCHANT_ID
        sync: false
      - key: PAYFAST_MERCHANT_KEY
        sync: false
      - key: COURIER_GUY_API_KEY
        sync: false
      - key: CLOUDINARY_CLOUD_NAME
        sync: false
      - key: CLOUDINARY_API_KEY
        sync: false
      - key: CLOUDINARY_API_SECRET
        sync: false
      - key: POKEMON_TCG_API_KEY
        sync: false
      - key: FRONTEND_URL
        sync: false
      - key: APP_ENV
        value: production
```

### Alembic Setup

**CRITICAL:** Alembic must use the session-mode connection string (port 5432), NOT transaction mode (port 6543). Transaction mode cannot run DDL like CREATE TABLE.

```python
# alembic/env.py — key change
from app.config import get_settings
from app.domain.models import Base  # Import all models

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url_sync)
target_metadata = Base.metadata
```

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### Create Seller Accounts Script

```python
# scripts/create_seller.py
"""Run once after first migration to create Brandon + Ruben seller accounts."""
import asyncio
from app.database import AsyncSessionLocal
from app.domain.models.user import User
from app.domain.enums import UserRole
from app.utils.security import hash_password

async def create_sellers():
    async with AsyncSessionLocal() as db:
        for name, email in [("Brandon", "brandon@example.com"), ("Ruben", "ruben@example.com")]:
            user = User(
                email=email, password_hash=hash_password("changeme123"),
                full_name=name, role=UserRole.SELLER,
            )
            db.add(user)
        await db.commit()
        print("✅ Seller accounts created. CHANGE PASSWORDS IMMEDIATELY.")

if __name__ == "__main__":
    asyncio.run(create_sellers())
```

---

## COMPLETE API ENDPOINT SUMMARY

| Method     | Endpoint                                       | Auth         | Description                                        |
| ---------- | ---------------------------------------------- | ------------ | -------------------------------------------------- |
| `POST`   | `/api/v1/auth/register`                      | —           | Register customer                                  |
| `POST`   | `/api/v1/auth/login`                         | —           | Login, get JWT                                     |
| `GET`    | `/api/v1/users/me`                           | Customer     | Get profile                                        |
| `PUT`    | `/api/v1/users/me`                           | Customer     | Update profile + address                           |
| `GET`    | `/api/v1/store/products`                     | —           | Browse with filters + pagination                   |
| `GET`    | `/api/v1/store/products/{id}`                | —           | Product detail                                     |
| `GET`    | `/api/v1/store/featured`                     | —           | Homepage featured products                         |
| `GET`    | `/api/v1/store/sets`                         | —           | All Pokemon TCG sets                               |
| `POST`   | `/api/v1/products/sealed`                    | Seller       | List sealed product                                |
| `POST`   | `/api/v1/products/single`                    | Seller       | List single card (auto-fetches from pokemontcg.io) |
| `POST`   | `/api/v1/products/{id}/photo`                | Seller       | Upload product photo to Cloudinary                 |
| `PUT`    | `/api/v1/products/{id}`                      | Seller       | Update product                                     |
| `DELETE` | `/api/v1/products/{id}`                      | Seller       | Delist product                                     |
| `GET`    | `/api/v1/products/inventory`                 | Seller       | Full inventory list                                |
| `GET`    | `/api/v1/products/inventory/stats`           | Seller       | Dashboard stats                                    |
| `GET`    | `/api/v1/products/search-tcg`                | Seller       | Search pokemontcg.io                               |
| `GET`    | `/api/v1/products/price-check/{tcg_id}`      | Seller       | Pricing breakdown before listing                   |
| `GET`    | `/api/v1/cart`                               | Customer     | View cart                                          |
| `POST`   | `/api/v1/cart/add`                           | Customer     | Add to cart                                        |
| `PUT`    | `/api/v1/cart/{item_id}`                     | Customer     | Update quantity                                    |
| `DELETE` | `/api/v1/cart/{item_id}`                     | Customer     | Remove item                                        |
| `DELETE` | `/api/v1/cart/clear`                         | Customer     | Clear cart                                         |
| `POST`   | `/api/v1/checkout/create-order`              | Optional     | Create order + get PayFast payment data            |
| `POST`   | `/api/v1/checkout/payfast/notify`            | — (PayFast) | Payment ITN webhook                                |
| `GET`    | `/api/v1/orders/my`                          | Customer     | My order history                                   |
| `GET`    | `/api/v1/orders/my/{order_number}`           | Customer     | My order detail                                    |
| `GET`    | `/api/v1/orders/track/{order_number}?email=` | —           | Guest order tracking                               |
| `GET`    | `/api/v1/orders/manage`                      | Seller       | All orders                                         |
| `PUT`    | `/api/v1/orders/manage/{id}/status`          | Seller       | Update order status                                |
| `PUT`    | `/api/v1/orders/manage/{id}/tracking`        | Seller       | Add tracking number manually                       |
| `POST`   | `/api/v1/shipping/quote`                     | —           | Live Courier Guy shipping quote                    |
| `POST`   | `/api/v1/shipping/book`                      | Seller       | Book Courier Guy collection                        |
| `POST`   | `/api/v1/shipping/webhook/courier-guy`       | — (webhook) | Courier status updates                             |
| `GET`    | `/api/v1/admin/exchange-rate`                | Seller       | Get USD→ZAR rate                                  |
| `PUT`    | `/api/v1/admin/exchange-rate`                | Seller       | Set USD→ZAR rate                                  |
| `GET`    | `/health`                                    | —           | Health check                                       |

---

## BUILD ORDER (STEP BY STEP)

Execute in this exact sequence. Test each step before moving on.

1. **Project scaffold** — Create directory structure, virtualenv, `pip install -r requirements.txt`
2. **Config + Database** — `config.py`, `database.py`, connect to Supabase
3. **Domain layer** — All enums, constants, models, schemas
4. **Alembic migration** — `alembic revision --autogenerate`, `alembic upgrade head`
5. **Utilities** — `security.py`, `pagination.py`, `exceptions.py`
6. **Base repository** — `base.py` with generic CRUD
7. **Auth flow** — `user_repo`, `auth_service`, `auth.py` router → test register + login
8. **Product CRUD** — `product_repo`, `pokemon_tcg_client`, `pricing_service`, `product_service`, `products.py` + `store.py` routers
9. **Image upload** — `cloudinary_client`, `image_service`, photo upload endpoint
10. **Cart** — `cart_repo`, `cart_service`, `cart.py` router
11. **Checkout** — `order_repo`, `order_service`, `payfast_client`, `payment_service`, `checkout.py` router
12. **PayFast webhook** — ITN handler, signature verification, stock reduction, auto-ship
13. **Shipping** — `courier_guy_client`, `shipping_service`, `shipping.py` router (quote + book + webhook)
14. **Order management** — `orders.py` router (customer + seller + guest tracking)
15. **Admin** — `admin.py` router (exchange rate)
16. **Seller setup** — Run `scripts/create_seller.py` to create Brandon + Ruben accounts
17. **Deploy** — Push to GitHub → Render auto-deploys → set env vars → verify `/health`

Use `/docs` (auto-generated Swagger UI) for manual testing at every step.

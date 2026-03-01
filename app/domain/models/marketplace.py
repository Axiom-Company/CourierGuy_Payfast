from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Float, Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.domain.models.base import Base, UUIDMixin, TimestampMixin


class SellerProfile(Base):
    __tablename__ = "seller_profiles"

    id: Mapped[str] = mapped_column(primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payfast_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)


class MarketplaceListing(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "marketplace_listings"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    sold_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    seller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    images: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reserve_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reserved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reserved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    promotion_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    promotion_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MarketplaceOrder(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "marketplace_orders"

    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    listing_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    seller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    buyer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)
    platform_fee: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    platform_fee_percentage: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    seller_amount: Mapped[float] = mapped_column(Float, nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="ZAR", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="created", nullable=False)
    payment_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    buyer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    buyer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    buyer_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shipping_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    payfast_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    listing_title: Mapped[str | None] = mapped_column(String(255), nullable=True)


class SellerPayout(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "seller_payouts"

    seller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="ZAR", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)


class ListingPromotion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "listing_promotions"

    listing_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    seller_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    price_paid: Mapped[float] = mapped_column(Float, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    payfast_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

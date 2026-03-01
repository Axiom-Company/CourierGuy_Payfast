from __future__ import annotations
from sqlalchemy import String, Float, Integer, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.domain.models.base import Base, UUIDMixin, TimestampMixin
from app.domain.enums import OrderStatus, PaymentStatus, ShippingMethod


class Order(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    # PKM-00001 display number
    order_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # Customer (nullable = guest checkout supported)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)

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

    # Payflex
    payment_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'payfast' | 'payflex'
    payflex_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    payflex_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payflex_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Notes
    seller_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    customer: Mapped["Customer | None"] = relationship(back_populates="orders", lazy="selectin")
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

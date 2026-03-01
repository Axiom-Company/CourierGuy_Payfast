from __future__ import annotations
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.domain.models.base import Base, UUIDMixin, TimestampMixin


class CartItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "cart_items"

    user_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    user: Mapped["Customer"] = relationship(back_populates="cart_items")
    product: Mapped["Product"] = relationship(lazy="selectin")

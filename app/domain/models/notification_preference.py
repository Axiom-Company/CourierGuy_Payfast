from __future__ import annotations
from sqlalchemy import String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.domain.models.base import Base, UUIDMixin

from datetime import datetime


class NotificationPreference(UUIDMixin, Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    order_updates: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    marketing_emails: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    restock_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    new_drops: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

from __future__ import annotations
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.domain.models.base import Base, UUIDMixin

from datetime import datetime


class EmailWebhookEvent(UUIDMixin, Base):
    __tablename__ = "email_webhook_events"

    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_reference: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    bounce_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    bounce_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

from __future__ import annotations
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.domain.models.base import Base, UUIDMixin

from datetime import datetime


class EmailLog(UUIDMixin, Base):
    __tablename__ = "email_logs"

    user_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sent")  # sent | failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

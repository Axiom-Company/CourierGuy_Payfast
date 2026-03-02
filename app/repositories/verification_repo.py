from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.marketplace import SellerVerification
from app.domain.models.user import Customer

logger = logging.getLogger(__name__)


class VerificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_latest_for_customer(self, customer_id: str) -> SellerVerification | None:
        """Get the most recent verification submission for a customer."""
        result = await self.db.execute(
            select(SellerVerification)
            .where(SellerVerification.customer_id == customer_id)
            .order_by(SellerVerification.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, verification_id: str) -> SellerVerification | None:
        result = await self.db.execute(
            select(SellerVerification).where(SellerVerification.id == verification_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> SellerVerification:
        verification = SellerVerification(**kwargs)
        self.db.add(verification)
        await self.db.flush()
        return verification

    async def update_verification(self, verification_id: str, **values) -> None:
        stmt = (
            update(SellerVerification)
            .where(SellerVerification.id == verification_id)
            .values(**values)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def list_by_status(
        self, status: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[SellerVerification]:
        """List verifications, optionally filtered by status."""
        query = select(SellerVerification).order_by(SellerVerification.created_at.desc())
        if status:
            query = query.where(SellerVerification.status == status)
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_by_status(self, status: str | None = None) -> int:
        from sqlalchemy import func
        query = select(func.count(SellerVerification.id))
        if status:
            query = query.where(SellerVerification.status == status)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def mark_customer_as_seller(self, customer_id: str) -> None:
        """Set is_seller=True and seller_verified_at on the customer."""
        stmt = (
            update(Customer)
            .where(Customer.id == customer_id)
            .values(
                is_seller=True,
                seller_verified_at=datetime.now(timezone.utc),
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def revoke_seller(self, customer_id: str) -> None:
        """Set is_seller=False on the customer (after rejection)."""
        stmt = (
            update(Customer)
            .where(Customer.id == customer_id)
            .values(is_seller=False, seller_verified_at=None)
        )
        await self.db.execute(stmt)
        await self.db.flush()

from __future__ import annotations

import logging
from sqlalchemy import select, text, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.models.marketplace import (
    MarketplaceListing,
    MarketplaceOrder,
    SellerPayout,
    SellerProfile,
    ListingPromotion,
)

logger = logging.getLogger(__name__)


class MarketplaceRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Listings ──

    async def get_active_listing(self, listing_id: str) -> MarketplaceListing | None:
        result = await self.db.execute(
            select(MarketplaceListing).where(
                MarketplaceListing.id == listing_id,
                MarketplaceListing.status == "active",
            )
        )
        return result.scalar_one_or_none()

    # ── Seller Profiles ──

    async def get_seller_profile_by_customer_id(self, customer_id: str) -> SellerProfile | None:
        result = await self.db.execute(
            select(SellerProfile).where(SellerProfile.customer_id == customer_id)
        )
        return result.scalar_one_or_none()

    # ── Reservations ──

    async def reserve_listing(self, listing_id: str, buyer_id: str | None, quantity: int) -> bool:
        try:
            result = await self.db.execute(
                text("SELECT reserve_listing(:lid, :bid, :qty)"),
                {"lid": listing_id, "bid": buyer_id, "qty": quantity},
            )
            row = result.scalar_one_or_none()
            return bool(row)
        except Exception:
            logger.exception("reserve_listing RPC failed for listing_id=%s", listing_id)
            return False

    async def release_reservation(self, listing_id: str) -> None:
        stmt = (
            update(MarketplaceListing)
            .where(MarketplaceListing.id == listing_id)
            .values(reserve_status=None, reserved_by=None, reserved_at=None)
        )
        await self.db.execute(stmt)

    # ── Marketplace Orders ──

    async def create_marketplace_order(self, **kwargs) -> MarketplaceOrder:
        order = MarketplaceOrder(**kwargs)
        self.db.add(order)
        await self.db.flush()
        return order

    async def get_marketplace_order(self, order_id: str) -> MarketplaceOrder | None:
        result = await self.db.execute(
            select(MarketplaceOrder).where(MarketplaceOrder.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_marketplace_order_by_number(self, order_number: str) -> MarketplaceOrder | None:
        result = await self.db.execute(
            select(MarketplaceOrder).where(MarketplaceOrder.order_number == order_number)
        )
        return result.scalar_one_or_none()

    async def update_marketplace_order(self, order_id: str, **values) -> MarketplaceOrder | None:
        stmt = (
            update(MarketplaceOrder)
            .where(MarketplaceOrder.id == order_id)
            .values(**values)
            .returning(MarketplaceOrder)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one_or_none()

    # ── Listing stock updates ──

    async def update_listing_after_sale(self, listing_id: str, quantity_sold: int) -> None:
        stmt = (
            update(MarketplaceListing)
            .where(MarketplaceListing.id == listing_id)
            .values(
                quantity=MarketplaceListing.quantity - quantity_sold,
                sold_quantity=MarketplaceListing.sold_quantity + quantity_sold,
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

        refreshed = await self.db.execute(
            select(MarketplaceListing.quantity).where(MarketplaceListing.id == listing_id)
        )
        remaining = refreshed.scalar_one_or_none()
        if remaining is not None and remaining <= 0:
            await self.db.execute(
                update(MarketplaceListing)
                .where(MarketplaceListing.id == listing_id)
                .values(status="sold", sold_at=func.now())
            )
            await self.db.flush()

    # ── Seller Payouts ──

    async def create_seller_payout(self, **kwargs) -> SellerPayout:
        payout = SellerPayout(**kwargs)
        self.db.add(payout)
        await self.db.flush()
        return payout

    # ── Promotions ──

    async def get_promotion(self, promotion_id: str) -> ListingPromotion | None:
        result = await self.db.execute(
            select(ListingPromotion).where(ListingPromotion.id == promotion_id)
        )
        return result.scalar_one_or_none()

    async def create_promotion(self, **kwargs) -> ListingPromotion:
        promo = ListingPromotion(**kwargs)
        self.db.add(promo)
        await self.db.flush()
        return promo

    async def update_promotion(self, promotion_id: str, **values) -> None:
        stmt = (
            update(ListingPromotion)
            .where(ListingPromotion.id == promotion_id)
            .values(**values)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def update_listing_promotion(self, listing_id: str, tier: str, expires_at) -> None:
        stmt = (
            update(MarketplaceListing)
            .where(MarketplaceListing.id == listing_id)
            .values(promotion_tier=tier, promotion_expires_at=expires_at)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_seller_promotions(self, seller_id: str) -> list[ListingPromotion]:
        result = await self.db.execute(
            select(ListingPromotion)
            .where(ListingPromotion.seller_id == seller_id)
            .order_by(ListingPromotion.created_at.desc())
        )
        return list(result.scalars().all())

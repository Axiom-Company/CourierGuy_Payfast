"""Marketplace listing promotions — ported from EliteTCG_API/routes/promotions.js."""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Request, HTTPException

from app.config import get_settings
from app.clients.payfast_client import PayFastClient
from app.domain.schemas.marketplace import PurchasePromotionRequest
from app.api.deps import get_marketplace_repo, get_email_service, get_current_user_id
from app.repositories.marketplace_repo import MarketplaceRepository
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/promotions", tags=["Promotions"])

PROMOTION_TIERS = {
    "spotlight": {"label": "Spotlight", "days": 3, "price": 25.0, "sort_priority": 1},
    "featured": {"label": "Featured", "days": 7, "price": 50.0, "sort_priority": 2},
    "premium": {"label": "Premium", "days": 14, "price": 75.0, "sort_priority": 3},
    "elite": {"label": "Elite Pin", "days": 30, "price": 100.0, "sort_priority": 4},
}


@router.get("/tiers")
async def get_tiers():
    return {"tiers": PROMOTION_TIERS}


@router.post("/purchase")
async def purchase_promotion(
    data: PurchasePromotionRequest,
    user_id: str = Depends(get_current_user_id),
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
):
    tier = PROMOTION_TIERS.get(data.tier)
    if not tier:
        raise HTTPException(400, f"Invalid tier: {data.tier}")

    listing = await repo.get_active_listing(data.listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")

    if listing.seller_id != user_id:
        # Check if user is the seller via seller_profile
        seller = await repo.get_seller_profile_by_customer_id(user_id)
        if not seller or listing.seller_id != seller.id:
            raise HTTPException(403, "Not authorized to promote this listing")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=tier["days"])

    promotion = await repo.create_promotion(
        listing_id=listing.id,
        seller_id=user_id,
        tier=data.tier,
        price_paid=tier["price"],
        starts_at=now,
        expires_at=expires_at,
        payment_status="pending",
    )

    settings = get_settings()
    payfast = PayFastClient()

    payment_data = payfast.generate_marketplace_payment_data(
        order_id=promotion.id,
        order_number=f"PROMO-{promotion.id[:8]}",
        total_zar=tier["price"],
        item_name=f"Promotion: {tier['label']} for {listing.title}",
        email="",  # Not needed for promotion purchases
        notify_url=settings.payfast_promo_notify_url,
        return_url=f"{settings.frontend_url}/marketplace/promotions?purchased=true",
        cancel_url=f"{settings.frontend_url}/marketplace/promotions",
    )

    return {
        "promotion": {
            "id": promotion.id,
            "tier": data.tier,
            "price_paid": tier["price"],
            "starts_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        },
        "payment_url": payfast.process_url,
        "payment_data": payment_data,
    }


@router.post("/notify")
async def promotion_itn(
    request: Request,
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    email_service: EmailService = Depends(get_email_service),
):
    form = await request.form()
    posted = dict(form)
    logger.info(f"[PROMO ITN] Received: m_payment_id={posted.get('m_payment_id')}")

    payfast = PayFastClient()
    if not payfast.verify_itn_signature(posted):
        logger.warning("[PROMO ITN] Invalid signature")
        return "OK"

    promotion_id = posted.get("m_payment_id", "")
    payment_status = posted.get("payment_status", "")

    promotion = await repo.get_promotion(promotion_id)
    if not promotion:
        logger.error(f"[PROMO ITN] Promotion not found: {promotion_id}")
        return "OK"

    if payment_status == "COMPLETE":
        expected = f"{promotion.price_paid:.2f}"
        received = posted.get("amount_gross", "0.00")
        if expected != received:
            logger.warning(f"[PROMO ITN] Amount mismatch: expected={expected} received={received}")
            return "OK"

        await repo.update_promotion(
            promotion_id,
            payment_status="completed",
            payfast_payment_id=posted.get("pf_payment_id"),
        )

        await repo.update_listing_promotion(
            promotion.listing_id, promotion.tier, promotion.expires_at,
        )

        logger.info(f"[PROMO ITN] Completed: {promotion_id} tier={promotion.tier}")

        # Send confirmation email
        try:
            listing = await repo.get_active_listing(promotion.listing_id)
            if listing:
                seller = await repo.get_seller_profile_by_customer_id(listing.seller_id)
                if seller:
                    seller_email = seller.contact_email or seller.payfast_email
                    if seller_email:
                        await email_service.send_promotion_confirmation(
                            seller_email, seller.display_name or "Seller",
                            listing.title, promotion.tier,
                            promotion.expires_at.isoformat() if promotion.expires_at else "",
                        )
        except Exception as e:
            logger.error(f"[PROMO ITN] Email failed: {e}")

    elif payment_status == "CANCELLED":
        await repo.update_promotion(promotion_id, payment_status="failed")
        logger.info(f"[PROMO ITN] Cancelled: {promotion_id}")

    return "OK"


@router.get("/my")
async def get_my_promotions(
    user_id: str = Depends(get_current_user_id),
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
):
    promotions = await repo.get_seller_promotions(user_id)
    return {
        "promotions": [
            {
                "id": p.id,
                "listing_id": p.listing_id,
                "tier": p.tier,
                "price_paid": p.price_paid,
                "starts_at": p.starts_at.isoformat() if p.starts_at else None,
                "expires_at": p.expires_at.isoformat() if p.expires_at else None,
                "payment_status": p.payment_status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in promotions
        ]
    }

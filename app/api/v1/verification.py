"""Seller identity verification endpoints.

Customer-facing:
  POST /verification/submit       — Submit ID + selfie for verification
  GET  /verification/status       — Check current verification status

Admin-facing:
  GET  /verification/admin/list   — List all verifications (filterable by status)
  GET  /verification/admin/{id}   — View full verification detail
  POST /verification/admin/{id}/decide — Approve or reject
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user_id, require_admin_api_key
from app.repositories.verification_repo import VerificationRepository
from app.database import get_db
from app.domain.schemas.verification import (
    SellerVerificationRequest,
    SellerVerificationStatusResponse,
    SellerVerificationSubmitResponse,
    AdminVerificationListItem,
    AdminVerificationDetail,
    AdminVerificationDecision,
)
from app.services.seller_verification_service import verify_seller_identity
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verification", tags=["Seller Verification"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> VerificationRepository:
    return VerificationRepository(db)


# ── Customer endpoints ──────────────────────────────────────────────────────


@router.post("/submit", response_model=SellerVerificationSubmitResponse)
async def submit_verification(
    body: SellerVerificationRequest,
    user_id: str = Depends(get_current_user_id),
    repo: VerificationRepository = Depends(_get_repo),
):
    """Submit ID document photos and a selfie for seller verification.

    The system will:
    1. Detect faces in the selfie and ID front
    2. OCR the ID front and back to extract name / ID number
    3. Store the results for admin review
    """
    # Check for existing pending/under_review submission
    existing = await repo.get_latest_for_customer(user_id)
    if existing and existing.status in ("pending", "under_review"):
        raise HTTPException(
            409,
            "You already have a verification in progress. "
            "Please wait for it to be reviewed.",
        )
    if existing and existing.status == "approved":
        raise HTTPException(409, "You are already verified as a seller.")

    # Run verification pipeline
    result = await verify_seller_identity(
        selfie_b64=body.selfie_image,
        id_front_b64=body.id_front_image,
        id_back_b64=body.id_back_image,
        id_type=body.id_type,
    )

    if "error" in result and "face_match_confidence" not in result:
        raise HTTPException(422, result["error"])

    # Determine initial status
    face_passed = result.get("face_match_passed", False)
    initial_status = "under_review" if face_passed else "pending"

    verification = await repo.create(
        customer_id=user_id,
        status=initial_status,
        id_type=body.id_type,
        id_front_image=body.id_front_image,
        id_back_image=body.id_back_image,
        selfie_image=body.selfie_image,
        id_number_hash=result.get("id_number_hash"),
        full_name_on_id=result.get("full_name_on_id"),
        ocr_text_front=result.get("ocr_text_front"),
        ocr_text_back=result.get("ocr_text_back"),
        face_match_confidence=result.get("face_match_confidence"),
        face_match_passed=face_passed,
        faces_detected_id=result.get("faces_detected_id"),
        faces_detected_selfie=result.get("faces_detected_selfie"),
    )

    message = (
        "Verification submitted successfully. Face match passed — awaiting admin review."
        if face_passed
        else "Verification submitted. Face match was inconclusive — an admin will review your documents manually."
    )

    return SellerVerificationSubmitResponse(
        verification_id=verification.id,
        status=verification.status,
        face_match_passed=face_passed,
        face_match_confidence=result.get("face_match_confidence"),
        message=message,
    )


@router.get("/status", response_model=SellerVerificationStatusResponse)
async def get_verification_status(
    user_id: str = Depends(get_current_user_id),
    repo: VerificationRepository = Depends(_get_repo),
    db: AsyncSession = Depends(get_db),
):
    """Get the current seller verification status for the logged-in user."""
    from app.domain.models.user import Customer
    from sqlalchemy import select

    # Check if already a seller
    cust_result = await db.execute(select(Customer).where(Customer.id == user_id))
    customer = cust_result.scalar_one_or_none()
    is_seller = bool(customer and customer.is_seller)

    verification = await repo.get_latest_for_customer(user_id)
    if not verification:
        return SellerVerificationStatusResponse(
            status="none",
            is_seller=is_seller,
        )

    return SellerVerificationStatusResponse(
        id=verification.id,
        status=verification.status,
        face_match_passed=verification.face_match_passed,
        face_match_confidence=verification.face_match_confidence,
        full_name_on_id=verification.full_name_on_id,
        rejection_reason=verification.rejection_reason,
        created_at=verification.created_at.isoformat() if verification.created_at else None,
        reviewed_at=verification.reviewed_at.isoformat() if verification.reviewed_at else None,
        is_seller=is_seller,
    )


# ── Admin endpoints ─────────────────────────────────────────────────────────


@router.get("/admin/list", response_model=list[AdminVerificationListItem])
async def admin_list_verifications(
    status: str | None = Query(None, description="Filter by status: pending, under_review, approved, rejected"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _=Depends(require_admin_api_key),
    repo: VerificationRepository = Depends(_get_repo),
):
    """List all seller verification submissions (admin only)."""
    verifications = await repo.list_by_status(status=status, limit=limit, offset=offset)
    total = await repo.count_by_status(status=status)

    items = []
    for v in verifications:
        items.append(AdminVerificationListItem(
            id=v.id,
            customer_id=v.customer_id,
            status=v.status,
            id_type=v.id_type,
            full_name_on_id=v.full_name_on_id,
            face_match_passed=v.face_match_passed,
            face_match_confidence=v.face_match_confidence,
            created_at=v.created_at.isoformat() if v.created_at else None,
            reviewed_at=v.reviewed_at.isoformat() if v.reviewed_at else None,
        ))
    return items


@router.get("/admin/{verification_id}", response_model=AdminVerificationDetail)
async def admin_get_verification(
    verification_id: str,
    _=Depends(require_admin_api_key),
    repo: VerificationRepository = Depends(_get_repo),
):
    """View full verification detail including images and OCR text (admin only)."""
    v = await repo.get_by_id(verification_id)
    if not v:
        raise HTTPException(404, "Verification not found")

    return AdminVerificationDetail(
        id=v.id,
        customer_id=v.customer_id,
        status=v.status,
        id_type=v.id_type,
        full_name_on_id=v.full_name_on_id,
        face_match_passed=v.face_match_passed,
        face_match_confidence=v.face_match_confidence,
        id_front_image=v.id_front_image,
        id_back_image=v.id_back_image,
        selfie_image=v.selfie_image,
        ocr_text_front=v.ocr_text_front,
        ocr_text_back=v.ocr_text_back,
        faces_detected_id=v.faces_detected_id,
        faces_detected_selfie=v.faces_detected_selfie,
        rejection_reason=v.rejection_reason,
        admin_notes=v.admin_notes,
        reviewed_by=v.reviewed_by,
        created_at=v.created_at.isoformat() if v.created_at else None,
        reviewed_at=v.reviewed_at.isoformat() if v.reviewed_at else None,
    )


@router.post("/admin/{verification_id}/decide")
async def admin_decide_verification(
    verification_id: str,
    body: AdminVerificationDecision,
    _=Depends(require_admin_api_key),
    repo: VerificationRepository = Depends(_get_repo),
):
    """Approve or reject a seller verification (admin only).

    On approval, the customer's is_seller flag is set to True.
    On rejection, the customer can resubmit with new documents.
    """
    v = await repo.get_by_id(verification_id)
    if not v:
        raise HTTPException(404, "Verification not found")

    if v.status in ("approved", "rejected"):
        raise HTTPException(409, f"Verification already {v.status}")

    now = datetime.now(timezone.utc)

    if body.action == "approve":
        await repo.update_verification(
            verification_id,
            status="approved",
            reviewed_at=now,
            reviewed_by="admin",
            admin_notes=body.admin_notes,
        )
        # Grant seller status
        await repo.mark_customer_as_seller(v.customer_id)

        return {
            "status": "approved",
            "customer_id": v.customer_id,
            "message": "Seller verification approved. Customer can now list items on the marketplace.",
        }

    else:  # reject
        if not body.rejection_reason:
            raise HTTPException(400, "rejection_reason is required when rejecting")

        await repo.update_verification(
            verification_id,
            status="rejected",
            reviewed_at=now,
            reviewed_by="admin",
            rejection_reason=body.rejection_reason,
            admin_notes=body.admin_notes,
        )
        # Revoke seller status if previously granted
        await repo.revoke_seller(v.customer_id)

        return {
            "status": "rejected",
            "customer_id": v.customer_id,
            "message": "Verification rejected. Customer can resubmit with new documents.",
        }


@router.get("/admin/stats")
async def admin_verification_stats(
    _=Depends(require_admin_api_key),
    repo: VerificationRepository = Depends(_get_repo),
):
    """Get verification statistics for the admin dashboard."""
    pending = await repo.count_by_status("pending")
    under_review = await repo.count_by_status("under_review")
    approved = await repo.count_by_status("approved")
    rejected = await repo.count_by_status("rejected")
    total = pending + under_review + approved + rejected

    return {
        "total": total,
        "pending": pending,
        "under_review": under_review,
        "approved": approved,
        "rejected": rejected,
    }

from __future__ import annotations

from pydantic import BaseModel, Field


class SellerVerificationRequest(BaseModel):
    """Submit ID + selfie for seller verification."""
    id_type: str = Field(
        ...,
        description="Type of ID document: sa_id, passport, or drivers_license",
        pattern="^(sa_id|passport|drivers_license)$",
    )
    id_front_image: str = Field(
        ..., min_length=100, description="Base64-encoded front of ID document"
    )
    id_back_image: str = Field(
        ..., min_length=100, description="Base64-encoded back of ID document"
    )
    selfie_image: str = Field(
        ..., min_length=100, description="Base64-encoded selfie photo for face verification"
    )


class SellerVerificationStatusResponse(BaseModel):
    """Current verification status for a user."""
    id: str | None = None
    status: str  # pending, under_review, approved, rejected
    face_match_passed: bool | None = None
    face_match_confidence: float | None = None
    full_name_on_id: str | None = None
    rejection_reason: str | None = None
    created_at: str | None = None
    reviewed_at: str | None = None
    is_seller: bool = False


class SellerVerificationSubmitResponse(BaseModel):
    """Response after submitting verification."""
    verification_id: str
    status: str
    face_match_passed: bool | None = None
    face_match_confidence: float | None = None
    message: str


# ── Admin schemas ──


class AdminVerificationListItem(BaseModel):
    """Summary item for admin verification list."""
    id: str
    customer_id: str
    status: str
    id_type: str
    full_name_on_id: str | None = None
    face_match_passed: bool | None = None
    face_match_confidence: float | None = None
    created_at: str | None = None
    reviewed_at: str | None = None


class AdminVerificationDetail(AdminVerificationListItem):
    """Full detail for admin review, including images and OCR text."""
    id_front_image: str | None = None
    id_back_image: str | None = None
    selfie_image: str | None = None
    ocr_text_front: str | None = None
    ocr_text_back: str | None = None
    faces_detected_id: int | None = None
    faces_detected_selfie: int | None = None
    rejection_reason: str | None = None
    admin_notes: str | None = None
    reviewed_by: str | None = None


class AdminVerificationDecision(BaseModel):
    """Admin approve or reject a verification."""
    action: str = Field(
        ...,
        description="approve or reject",
        pattern="^(approve|reject)$",
    )
    rejection_reason: str | None = Field(
        None, description="Required when rejecting"
    )
    admin_notes: str | None = None

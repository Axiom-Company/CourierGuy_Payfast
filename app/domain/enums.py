from enum import Enum


class ProductType(str, Enum):
    SEALED = "sealed"
    SINGLE = "single"


class SealedCategory(str, Enum):
    BOOSTER_BOX = "booster_box"
    BOOSTER_PACK = "booster_pack"
    ETB = "etb"
    COLLECTION = "collection"
    TIN = "tin"
    BUNDLE = "bundle"
    OTHER = "other"


class CardCondition(str, Enum):
    MINT = "Mint"
    NEAR_MINT = "NM"
    LIGHTLY_PLAYED = "LP"
    MODERATELY_PLAYED = "MP"
    HEAVILY_PLAYED = "HP"
    DAMAGED = "Damaged"


class OrderStatus(str, Enum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ShippingMethod(str, Enum):
    COLLECTION = "collection"
    COURIER_GUY = "courier_guy"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class IDType(str, Enum):
    SA_ID = "sa_id"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"


class UserRole(str, Enum):
    USER = "user"
    SELLER = "seller"
    VERIFIED_SELLER = "verified_seller"
    ADMIN = "admin"

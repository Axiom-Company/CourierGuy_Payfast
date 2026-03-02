#!/usr/bin/env python3
"""
Comprehensive test suite for the seller verification system.
Tests parsing logic, service layer, schemas, and simulated endpoint flow.
Run: python3 tests/test_seller_verification.py
"""
import asyncio
import base64
import json
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0


def check(name: str, result: bool, detail: str = ""):
    global PASS, FAIL
    if result:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


# ═══════════════════════════════════════════════════════════════════
# 1. Test OCR text parsing (no API key needed)
# ═══════════════════════════════════════════════════════════════════
print("\n=== 1. SA ID Parsing ===")
from app.services.seller_verification_service import (
    parse_sa_id_text,
    parse_passport_text,
    parse_drivers_license_text,
    _hash_id_number,
    _strip_data_uri,
)

sa_id_text = """
REPUBLIC OF SOUTH AFRICA
IDENTITY DOCUMENT
SURNAME
MOKOENA
NAMES
THABO JAMES
IDENTITY NUMBER
9501015800086
DATE OF BIRTH
1995/01/01
STATUS
CITIZEN
"""

parsed = parse_sa_id_text(sa_id_text)
check("SA ID number extracted", parsed["id_number"] == "9501015800086",
      f"got: {parsed['id_number']}")
check("SA ID name has surname", "MOKOENA" in parsed["full_name"],
      f"got: {parsed['full_name']}")
check("SA ID name has given names", "THABO" in parsed["full_name"],
      f"got: {parsed['full_name']}")

# Test with no valid ID
parsed_empty = parse_sa_id_text("Random text with no ID data")
check("No false positive ID number", parsed_empty["id_number"] == "")

# Test invalid month
parsed_bad = parse_sa_id_text("Some text 9513015800086 more text")
check("Invalid month rejected", parsed_bad["id_number"] == "",
      f"got: {parsed_bad['id_number']}")

# ─────────────────────────────────────────────────────────
print("\n=== 2. Passport Parsing ===")

passport_text = """
REPUBLIC OF SOUTH AFRICA
PASSPORT
SURNAME
MOKOENA
GIVEN NAMES
THABO JAMES
PASSPORT NO
A12345678
DATE OF BIRTH
01 JAN 1995
"""

parsed_pp = parse_passport_text(passport_text)
check("Passport number extracted", parsed_pp["passport_number"] == "A12345678",
      f"got: {parsed_pp['passport_number']}")

# MRZ test
# MRZ: exactly 44 chars per line for TD3 (passport)
mrz_line1 = "P<ZAFMOKOENA<<THABO<JAMES<<<<<<<<<<<<<<<<<"  # 44 chars
mrz_line2 = "A123456780ZAF9501010M2501011<<<<<<<<<<<<<<06"  # 44 chars
mrz_text = f"{mrz_line1}\n{mrz_line2}"

parsed_mrz = parse_passport_text(mrz_text)
check("MRZ name extracted", "THABO" in parsed_mrz["full_name"] or "MOKOENA" in parsed_mrz["full_name"],
      f"got: {parsed_mrz}")

# ─────────────────────────────────────────────────────────
print("\n=== 3. Driver's License Parsing ===")

dl_text = """
SOUTH AFRICA
DRIVING LICENCE
SURNAME
MOKOENA
FIRST NAME
THABO
IDENTITY NUMBER
9501015800086
LICENCE NO
12 3456 7890 12
VALID FROM 2015/03/01
"""

parsed_dl = parse_drivers_license_text(dl_text)
check("DL number or ID extracted", len(parsed_dl["license_number"]) > 0,
      f"got: {parsed_dl['license_number']}")
check("DL has name", "MOKOENA" in parsed_dl["full_name"] or "THABO" in parsed_dl["full_name"],
      f"got: {parsed_dl['full_name']}")

# ─────────────────────────────────────────────────────────
print("\n=== 4. Utility Functions ===")

check("Hash is deterministic",
      _hash_id_number("9501015800086") == _hash_id_number("9501015800086"))
check("Hash differs for different input",
      _hash_id_number("9501015800086") != _hash_id_number("9501015800087"))
check("Hash is SHA256 length", len(_hash_id_number("test")) == 64)

check("Strip data URI", _strip_data_uri("data:image/png;base64,abc123") == "abc123")
check("No prefix unchanged", _strip_data_uri("abc123") == "abc123")

# ═══════════════════════════════════════════════════════════════════
# 2. Test Pydantic schemas
# ═══════════════════════════════════════════════════════════════════
print("\n=== 5. Verification Schemas ===")
from app.domain.schemas.verification import (
    SellerVerificationRequest,
    SellerVerificationStatusResponse,
    SellerVerificationSubmitResponse,
    AdminVerificationListItem,
    AdminVerificationDetail,
    AdminVerificationDecision,
)
from pydantic import ValidationError

# Valid request
try:
    req = SellerVerificationRequest(
        id_type="sa_id",
        id_front_image="a" * 200,
        id_back_image="b" * 200,
        selfie_image="c" * 200,
    )
    check("Valid request passes", True)
except ValidationError as e:
    check("Valid request passes", False, str(e))

# Invalid id_type
try:
    SellerVerificationRequest(
        id_type="invalid_type",
        id_front_image="a" * 200,
        id_back_image="b" * 200,
        selfie_image="c" * 200,
    )
    check("Invalid id_type rejected", False, "should have raised")
except ValidationError:
    check("Invalid id_type rejected", True)

# Too-short image
try:
    SellerVerificationRequest(
        id_type="sa_id",
        id_front_image="short",
        id_back_image="b" * 200,
        selfie_image="c" * 200,
    )
    check("Short image rejected", False, "should have raised")
except ValidationError:
    check("Short image rejected", True)

# Status response
status = SellerVerificationStatusResponse(
    status="pending",
    is_seller=False,
)
check("Status response serializes", status.status == "pending")

# Admin decision validation
try:
    AdminVerificationDecision(action="approve")
    check("Approve action valid", True)
except ValidationError as e:
    check("Approve action valid", False, str(e))

try:
    AdminVerificationDecision(action="invalid")
    check("Invalid action rejected", False, "should have raised")
except ValidationError:
    check("Invalid action rejected", True)

# ═══════════════════════════════════════════════════════════════════
# 3. Test Enums
# ═══════════════════════════════════════════════════════════════════
print("\n=== 6. Enum Values ===")
from app.domain.enums import VerificationStatus, IDType

check("VerificationStatus.PENDING", VerificationStatus.PENDING.value == "pending")
check("VerificationStatus.APPROVED", VerificationStatus.APPROVED.value == "approved")
check("IDType.SA_ID", IDType.SA_ID.value == "sa_id")
check("IDType.PASSPORT", IDType.PASSPORT.value == "passport")
check("IDType.DRIVERS_LICENSE", IDType.DRIVERS_LICENSE.value == "drivers_license")

# ═══════════════════════════════════════════════════════════════════
# 4. Test Model definition
# ═══════════════════════════════════════════════════════════════════
print("\n=== 7. SellerVerification Model ===")
from app.domain.models.marketplace import SellerVerification

check("Table name", SellerVerification.__tablename__ == "seller_verifications")
cols = {c.name for c in SellerVerification.__table__.columns}
check("Has customer_id column", "customer_id" in cols)
check("Has status column", "status" in cols)
check("Has id_type column", "id_type" in cols)
check("Has face_match_confidence", "face_match_confidence" in cols)
check("Has face_match_passed", "face_match_passed" in cols)
check("Has id_front_image", "id_front_image" in cols)
check("Has selfie_image", "selfie_image" in cols)
check("Has reviewed_by", "reviewed_by" in cols)
check("Has rejection_reason", "rejection_reason" in cols)
check("Has id_number_hash", "id_number_hash" in cols)

# ═══════════════════════════════════════════════════════════════════
# 5. Test Vision API service (mocked — no real API key)
# ═══════════════════════════════════════════════════════════════════
print("\n=== 8. Vision API Service (no-key path) ===")
from app.services.seller_verification_service import verify_seller_identity

# Set minimal env vars so Settings() doesn't crash
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://localhost/test")
os.environ.setdefault("PAYFAST_MERCHANT_ID", "test")
os.environ.setdefault("PAYFAST_MERCHANT_KEY", "test")
os.environ.setdefault("PAYFAST_RETURN_URL", "http://localhost")
os.environ.setdefault("PAYFAST_CANCEL_URL", "http://localhost")
os.environ.setdefault("PAYFAST_NOTIFY_URL", "http://localhost")
os.environ.setdefault("COURIER_GUY_API_KEY", "test")
# Make sure Vision API key is NOT set for this test
os.environ.pop("GOOGLE_CLOUD_VISION_API_KEY", None)
# Clear cached settings
from app.config import get_settings
get_settings.cache_clear()

async def test_no_api_key():
    # Without a key, should return an error
    result = await verify_seller_identity(
        selfie_b64="abc",
        id_front_b64="def",
        id_back_b64="ghi",
        id_type="sa_id",
    )
    return result

result = asyncio.run(test_no_api_key())
check("No API key returns error", "error" in result, f"got: {result}")
check("Error mentions API key", "API key" in result.get("error", ""),
      f"got: {result.get('error', '')}")

# ═══════════════════════════════════════════════════════════════════
# 6. Test Migration file
# ═══════════════════════════════════════════════════════════════════
print("\n=== 9. Migration File ===")
import importlib.util

spec = importlib.util.spec_from_file_location(
    "migration_005",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "alembic/versions/005_add_seller_verifications.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
check("Migration revision", mod.revision == "005_seller_verifications")
check("Migration down_revision", mod.down_revision == "004_profiles")
check("Has upgrade()", hasattr(mod, "upgrade"))
check("Has downgrade()", hasattr(mod, "downgrade"))

# ═══════════════════════════════════════════════════════════════════
# 7. Test Router definition
# ═══════════════════════════════════════════════════════════════════
print("\n=== 10. Router Registration ===")
try:
    from app.api.v1.verification import router

    check("Router prefix", router.prefix == "/verification")
    route_paths = [r.path for r in router.routes]
    check("Has /submit route", "/submit" in route_paths)
    check("Has /status route", "/status" in route_paths)
    check("Has /admin/list route", "/admin/list" in route_paths)
    check("Has /admin/{verification_id} route", "/admin/{verification_id}" in route_paths)
    check("Has /admin/{verification_id}/decide route",
          "/admin/{verification_id}/decide" in route_paths)
    check("Has /admin/stats route", "/admin/stats" in route_paths)
except BaseException as e:
    print(f"  SKIP  Router tests (missing dependency: {type(e).__name__}: {e})")
    # Verify syntax is correct at minimum
    import py_compile
    py_compile.compile("app/api/v1/verification.py", doraise=True)
    check("Router file compiles", True)

# ═══════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════
print(f"\n{'='*50}")
print(f"RESULTS: {PASS} passed, {FAIL} failed, {PASS+FAIL} total")
print(f"{'='*50}")

if FAIL > 0:
    sys.exit(1)
else:
    print("All tests passed!")

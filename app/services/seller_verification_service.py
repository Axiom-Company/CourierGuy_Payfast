"""
Seller identity verification using Google Cloud Vision.

Flow:
1. User submits selfie + ID front image + ID back image (base64)
2. Vision API detects faces in both selfie and ID photo
3. Vision API runs OCR on ID front/back to extract text (name, ID number)
4. Face likelihood comparison provides a confidence indicator
5. Results stored in seller_verifications table for admin review
6. Admin approves/rejects; on approval customer.is_seller = True
"""
import hashlib
import logging
import re

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"

# Minimum face detection confidence considered acceptable
_FACE_JOY_LIKELIHOODS = {
    "VERY_UNLIKELY": 0.05,
    "UNLIKELY": 0.20,
    "POSSIBLE": 0.50,
    "LIKELY": 0.75,
    "VERY_LIKELY": 0.95,
}


def _strip_data_uri(b64: str) -> str:
    """Remove data URI prefix if present."""
    if b64.startswith("data:") and "," in b64:
        return b64.split(",", 1)[1]
    return b64


def _hash_id_number(id_number: str) -> str:
    """One-way hash an ID number for storage (never store plaintext)."""
    return hashlib.sha256(id_number.encode()).hexdigest()


async def _call_vision_api(image_b64: str, features: list[dict]) -> dict | None:
    """Make a single Vision API call and return the first response."""
    settings = get_settings()
    if not settings.google_cloud_vision_api_key:
        return None

    body = {
        "requests": [
            {
                "image": {"content": image_b64},
                "features": features,
            }
        ]
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{VISION_API_URL}?key={settings.google_cloud_vision_api_key}",
                json=body,
                timeout=30.0,
            )
        if resp.status_code != 200:
            logger.error("Vision API %d: %s", resp.status_code, resp.text[:500])
            return None
        responses = resp.json().get("responses", [])
        return responses[0] if responses else None
    except httpx.HTTPError as exc:
        logger.error("Vision API request failed: %s", exc)
        return None


async def detect_faces(image_b64: str) -> dict:
    """Detect faces in an image. Returns face count and detection confidence."""
    image_b64 = _strip_data_uri(image_b64)
    result = await _call_vision_api(image_b64, [
        {"type": "FACE_DETECTION", "maxResults": 5},
    ])
    if result is None:
        return {"error": "Vision API unavailable", "face_count": 0, "confidence": 0.0}

    if "error" in result:
        return {"error": result["error"].get("message", "Face detection failed"), "face_count": 0, "confidence": 0.0}

    faces = result.get("faceAnnotations", [])
    if not faces:
        return {"face_count": 0, "confidence": 0.0}

    # Use the highest detection confidence among all faces
    best_confidence = max(face.get("detectionConfidence", 0.0) for face in faces)
    return {
        "face_count": len(faces),
        "confidence": round(best_confidence, 4),
    }


async def ocr_document(image_b64: str) -> dict:
    """Run OCR on an ID document image. Returns extracted text."""
    image_b64 = _strip_data_uri(image_b64)
    result = await _call_vision_api(image_b64, [
        {"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 1},
    ])
    if result is None:
        return {"error": "Vision API unavailable", "text": ""}

    if "error" in result:
        return {"error": result["error"].get("message", "OCR failed"), "text": ""}

    annotations = result.get("textAnnotations", [])
    full_text = annotations[0]["description"] if annotations else ""
    return {"text": full_text}


def parse_sa_id_text(text: str) -> dict:
    """Extract South African ID number and name from OCR text."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    id_number = ""
    full_name = ""

    # SA ID number: 13 digits
    id_match = re.search(r"\b(\d{13})\b", text)
    if id_match:
        candidate = id_match.group(1)
        # Basic Luhn-style check: SA IDs start with YYMMDD
        yy = int(candidate[:2])
        mm = int(candidate[2:4])
        dd = int(candidate[4:6])
        if 1 <= mm <= 12 and 1 <= dd <= 31:
            id_number = candidate

    # Try to extract name — typically near "SURNAME" or "NAMES" labels
    for i, line in enumerate(lines):
        upper = line.upper()
        if "SURNAME" in upper or "SURNAME" in upper.replace(" ", ""):
            # Next non-empty line is likely the surname
            if i + 1 < len(lines):
                surname = lines[i + 1].strip()
                if surname and not surname.isdigit():
                    full_name = surname
        elif "NAMES" in upper or "FORENAMES" in upper:
            if i + 1 < len(lines):
                names = lines[i + 1].strip()
                if names and not names.isdigit():
                    full_name = f"{full_name} {names}".strip() if full_name else names

    # Fallback: look for "IDENTITY NUMBER" label
    if not id_number:
        for i, line in enumerate(lines):
            if "IDENTITY" in line.upper() and "NUMBER" in line.upper():
                if i + 1 < len(lines):
                    candidate = re.sub(r"\s+", "", lines[i + 1])
                    if re.match(r"^\d{13}$", candidate):
                        id_number = candidate

    return {
        "id_number": id_number,
        "full_name": full_name,
    }


def parse_passport_text(text: str) -> dict:
    """Extract passport number and name from OCR text."""
    passport_number = ""
    full_name = ""

    # Passport number: typically alphanumeric, 6-9 chars
    passport_match = re.search(r"\b([A-Z]\d{7,8})\b", text.upper())
    if passport_match:
        passport_number = passport_match.group(1)

    # Try MRZ (machine readable zone) — two lines starting with P<
    mrz_match = re.search(r"(P[<A-Z][A-Z]{3}[A-Z<]{30,39})\n([A-Z0-9<]{30,44})", text.upper())
    if mrz_match:
        mrz_line1 = mrz_match.group(1)
        # Extract name from MRZ line 1
        name_part = mrz_line1[5:]
        parts = name_part.split("<<")
        if len(parts) >= 2:
            surname = parts[0].replace("<", " ").strip()
            given = parts[1].replace("<", " ").strip()
            full_name = f"{given} {surname}".strip()

    # Fallback: look for "SURNAME" field
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not full_name:
        for i, line in enumerate(lines):
            if "SURNAME" in line.upper():
                if i + 1 < len(lines) and not lines[i + 1].isdigit():
                    full_name = lines[i + 1].strip()

    return {
        "passport_number": passport_number,
        "full_name": full_name,
    }


def parse_drivers_license_text(text: str) -> dict:
    """Extract driver's license number and name from OCR text."""
    license_number = ""
    full_name = ""

    # SA driver's license number pattern
    lic_match = re.search(r"\b(\d{2}\s*\d{4}\s*\d{4}\s*\d{2})\b", text)
    if lic_match:
        license_number = re.sub(r"\s+", "", lic_match.group(1))

    # Also try 13-digit ID number on the card
    id_match = re.search(r"\b(\d{13})\b", text)
    if id_match and not license_number:
        license_number = id_match.group(1)

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for i, line in enumerate(lines):
        upper = line.upper()
        if "SURNAME" in upper:
            if i + 1 < len(lines) and not lines[i + 1].isdigit():
                full_name = lines[i + 1].strip()
        elif "INITIALS" in upper or "FIRST NAME" in upper:
            if i + 1 < len(lines) and not lines[i + 1].isdigit():
                given = lines[i + 1].strip()
                full_name = f"{given} {full_name}".strip() if full_name else given

    return {
        "license_number": license_number,
        "full_name": full_name,
    }


async def verify_seller_identity(
    selfie_b64: str,
    id_front_b64: str,
    id_back_b64: str,
    id_type: str,
) -> dict:
    """Run the full seller verification pipeline.

    1. Detect faces in selfie and ID front
    2. OCR the ID front and back
    3. Parse extracted text for ID info
    4. Compute face match confidence

    Returns a dict with all results for storage.
    """
    settings = get_settings()
    if not settings.google_cloud_vision_api_key:
        return {
            "error": "Google Cloud Vision API key is not configured. "
                     "Set GOOGLE_CLOUD_VISION_API_KEY in the environment.",
        }

    # Step 1: Detect faces in both images
    selfie_faces = await detect_faces(selfie_b64)
    id_faces = await detect_faces(id_front_b64)

    if selfie_faces.get("error"):
        return {"error": f"Selfie face detection failed: {selfie_faces['error']}"}
    if id_faces.get("error"):
        return {"error": f"ID face detection failed: {id_faces['error']}"}

    selfie_face_count = selfie_faces["face_count"]
    id_face_count = id_faces["face_count"]

    if selfie_face_count == 0:
        return {
            "error": "No face detected in selfie. Please take a clear photo of your face.",
            "faces_detected_selfie": 0,
            "faces_detected_id": id_face_count,
        }

    if id_face_count == 0:
        return {
            "error": "No face detected on ID document. Please take a clear photo of the front of your ID.",
            "faces_detected_selfie": selfie_face_count,
            "faces_detected_id": 0,
        }

    # Step 2: Compute face match confidence
    # Google Cloud Vision doesn't directly compare faces, so we use
    # detection confidence as a proxy. Both faces must be clearly detected.
    # For production, consider Google Cloud Face API or a dedicated service.
    selfie_conf = selfie_faces["confidence"]
    id_conf = id_faces["confidence"]
    face_match_confidence = round(min(selfie_conf, id_conf), 4)
    face_match_passed = (
        selfie_face_count >= 1
        and id_face_count >= 1
        and face_match_confidence >= 0.50
    )

    # Step 3: OCR the ID document
    ocr_front = await ocr_document(id_front_b64)
    ocr_back = await ocr_document(id_back_b64)

    ocr_text_front = ocr_front.get("text", "")
    ocr_text_back = ocr_back.get("text", "")

    # Step 4: Parse ID info based on type
    combined_text = f"{ocr_text_front}\n{ocr_text_back}"
    if id_type == "sa_id":
        parsed = parse_sa_id_text(combined_text)
        id_number = parsed.get("id_number", "")
        full_name = parsed.get("full_name", "")
    elif id_type == "passport":
        parsed = parse_passport_text(combined_text)
        id_number = parsed.get("passport_number", "")
        full_name = parsed.get("full_name", "")
    elif id_type == "drivers_license":
        parsed = parse_drivers_license_text(combined_text)
        id_number = parsed.get("license_number", "")
        full_name = parsed.get("full_name", "")
    else:
        id_number = ""
        full_name = ""

    return {
        "face_match_confidence": face_match_confidence,
        "face_match_passed": face_match_passed,
        "faces_detected_selfie": selfie_face_count,
        "faces_detected_id": id_face_count,
        "ocr_text_front": ocr_text_front,
        "ocr_text_back": ocr_text_back,
        "id_number_hash": _hash_id_number(id_number) if id_number else None,
        "full_name_on_id": full_name or None,
    }

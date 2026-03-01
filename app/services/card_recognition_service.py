"""
Google Cloud Vision OCR for camera-based Pokemon card scanning.
Uses the REST API directly via httpx (no heavy google-cloud-vision SDK).
"""
import logging
import re
import httpx
from app.config import get_settings
from app.clients.pokemon_tcg_client import PokemonTCGClient

logger = logging.getLogger(__name__)

VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"

_tcg_client = PokemonTCGClient()


async def scan_card_image(image_base64: str) -> dict:
    """Scan a Pokemon card image using Google Cloud Vision OCR.

    Args:
        image_base64: Base64-encoded image data (no data URI prefix).

    Returns:
        Dict with extracted text, matched cards, and confidence info.
    """
    settings = get_settings()

    if not settings.google_cloud_vision_api_key:
        return {
            "error": "Google Cloud Vision API key is not configured. "
                     "Set GOOGLE_CLOUD_VISION_API_KEY in the environment.",
            "matched_cards": [],
        }

    # Strip data URI prefix if present
    if "," in image_base64 and image_base64.startswith("data:"):
        image_base64 = image_base64.split(",", 1)[1]

    request_body = {
        "requests": [
            {
                "image": {"content": image_base64},
                "features": [
                    {"type": "TEXT_DETECTION", "maxResults": 10},
                    {"type": "LABEL_DETECTION", "maxResults": 10},
                ],
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{VISION_API_URL}?key={settings.google_cloud_vision_api_key}",
                json=request_body,
                timeout=20.0,
            )

            if resp.status_code != 200:
                logger.error("Vision API returned status %d: %s", resp.status_code, resp.text[:500])
                return {
                    "error": "Card scanning service unavailable",
                    "matched_cards": [],
                }

            data = resp.json()

    except httpx.HTTPError as exc:
        logger.error("Vision API request failed: %s", exc)
        return {
            "error": "Card scanning service unavailable",
            "matched_cards": [],
        }

    responses = data.get("responses", [])
    if not responses:
        return {"error": "No response from Vision API", "matched_cards": []}

    response = responses[0]

    # Check for API-level errors
    if "error" in response:
        logger.error("Vision API error: %s", response["error"].get("message", ""))
        return {"error": "Card scanning failed", "matched_cards": []}

    # Extract OCR text
    text_annotations = response.get("textAnnotations", [])
    full_text = text_annotations[0]["description"] if text_annotations else ""

    # Extract labels
    labels = [
        label.get("description", "")
        for label in response.get("labelAnnotations", [])
    ]

    # Parse card info from OCR text
    card_name, set_info, card_number = _parse_card_text(full_text)

    # Search pokemontcg.io with extracted data
    matched_cards = []
    if card_name:
        search_result = await _tcg_client.search_cards(card_name)
        matched_cards = search_result.get("data", [])[:5]

    return {
        "ocr_text": full_text,
        "labels": labels,
        "extracted": {
            "card_name": card_name,
            "set_info": set_info,
            "card_number": card_number,
        },
        "matched_cards": matched_cards,
        "match_count": len(matched_cards),
    }


def _parse_card_text(text: str) -> tuple[str, str, str]:
    """Parse OCR text to extract card name, set info, and card number.

    Returns (card_name, set_info, card_number). Any may be empty string.
    """
    if not text:
        return ("", "", "")

    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]

    card_name = ""
    set_info = ""
    card_number = ""

    # Card name is typically the first prominent line (not a number, not HP)
    for line in lines:
        cleaned = line.strip()
        if not cleaned:
            continue
        # Skip lines that are just numbers, HP values, or very short
        if re.match(r"^\d+$", cleaned):
            continue
        if re.match(r"^\d+\s*HP$", cleaned, re.IGNORECASE):
            continue
        if len(cleaned) < 2:
            continue
        card_name = cleaned
        break

    # Look for card number pattern: digits/digits (e.g. "025/198")
    number_match = re.search(r"(\d{1,4})\s*/\s*(\d{1,4})", text)
    if number_match:
        card_number = number_match.group(1).lstrip("0") or "0"
        set_info = f"{number_match.group(1)}/{number_match.group(2)}"

    # Also try "No. XX" or "#XX" patterns
    if not card_number:
        alt_match = re.search(r"(?:No\.|#)\s*(\d+)", text, re.IGNORECASE)
        if alt_match:
            card_number = alt_match.group(1).lstrip("0") or "0"

    return (card_name, set_info, card_number)

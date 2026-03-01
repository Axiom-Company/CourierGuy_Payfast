import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.clients.pokemon_tcg_client import PokemonTCGClient
from app.services import exchange_rate_service, commission_service, card_evaluation_service
from app.services.card_recognition_service import scan_card_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cards", tags=["Cards"])

_tcg_client = PokemonTCGClient()


# ── Request schemas ──────────────────────────────────────────────────────────


class ScanRequest(BaseModel):
    image: str = Field(..., min_length=1, description="Base64-encoded card image")


class CommissionPreviewRequest(BaseModel):
    price_zar: float = Field(..., gt=0, description="Price in ZAR")


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/search")
async def search_cards(
    q: str = Query(..., min_length=1, max_length=200, description="Card name search query"),
    set_id: str | None = Query(None, max_length=50, description="Optional set ID filter"),
    db: AsyncSession = Depends(get_db),
):
    """Search Pokemon TCG cards by name. Prices returned in ZAR."""
    try:
        result = await _tcg_client.search_cards(q, set_id=set_id)
    except Exception as exc:
        logger.error("Card search failed: %s", exc)
        raise HTTPException(503, "Card search service unavailable")

    rate = await exchange_rate_service.get_current_rate(db)

    cards = result.get("data", [])
    for card in cards:
        usd = card.get("market_price_usd")
        card["market_price_zar"] = round(usd * rate, 2) if usd else None
        card["exchange_rate"] = round(rate, 4)

    return {"cards": cards, "total": result.get("totalCount", 0)}


@router.get("/sets")
async def get_sets():
    """Get all Pokemon TCG sets, newest first."""
    try:
        sets = await _tcg_client.get_sets()
    except Exception as exc:
        logger.error("Get sets failed: %s", exc)
        raise HTTPException(503, "Card set service unavailable")
    return {"data": sets, "count": len(sets)}


@router.get("/lookup/{set_id}/{number}")
async def lookup_card(
    set_id: str,
    number: str,
    db: AsyncSession = Depends(get_db),
):
    """Lookup a specific card by set ID and number. Returns ZAR price."""
    try:
        card = await _tcg_client.lookup_card(set_id, number)
    except Exception as exc:
        logger.error("Card lookup failed: %s", exc)
        raise HTTPException(503, "Card lookup service unavailable")

    if card is None:
        raise HTTPException(404, f"Card {set_id}-{number} not found")

    rate = await exchange_rate_service.get_current_rate(db)
    usd = card.get("market_price_usd")
    card["market_price_zar"] = round(usd * rate, 2) if usd else None
    card["exchange_rate"] = round(rate, 4)

    return card


@router.get("/evaluate/{set_id}/{number}")
async def evaluate_card(
    set_id: str,
    number: str,
    condition: str = Query("NM", description="Card condition: Mint, NM, LP, MP, HP, Damaged"),
    db: AsyncSession = Depends(get_db),
):
    """Full card evaluation with condition-adjusted pricing and commission breakdown."""
    try:
        result = await card_evaluation_service.evaluate_card(
            set_id, number, condition, db
        )
    except Exception as exc:
        logger.error("Card evaluation failed: %s", exc)
        raise HTTPException(503, "Card evaluation service unavailable")

    if "error" in result and "card" not in result:
        raise HTTPException(404, result["error"])

    return result


@router.post("/scan")
async def scan_card(body: ScanRequest):
    """Scan a Pokemon card image using OCR to identify the card."""
    try:
        result = await scan_card_image(body.image)
    except Exception as exc:
        logger.error("Card scan failed: %s", exc)
        raise HTTPException(503, "Card scanning service unavailable")

    if "error" in result and not result.get("matched_cards"):
        raise HTTPException(
            422 if "not configured" in result.get("error", "") else 503,
            result["error"],
        )

    # Remap matched_cards → matches for frontend compatibility
    return {
        "matches": result.get("matched_cards", []),
        "match_count": result.get("match_count", 0),
        "extracted": result.get("extracted"),
        "ocr_text": result.get("ocr_text"),
    }


@router.get("/exchange-rate")
async def get_exchange_rate(db: AsyncSession = Depends(get_db)):
    """Get current USD to ZAR exchange rate."""
    try:
        rate = await exchange_rate_service.get_current_rate(db)
    except Exception as exc:
        logger.error("Exchange rate fetch failed: %s", exc)
        raise HTTPException(503, "Exchange rate service unavailable")

    return {
        "from": "USD",
        "to": "ZAR",
        "rate": round(rate, 4),
    }


@router.post("/commission-preview")
async def commission_preview(body: CommissionPreviewRequest):
    """Preview the marketplace commission for a given ZAR price."""
    return commission_service.calculate_commission(body.price_zar)

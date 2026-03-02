import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import get_settings
from app.api.router import api_router
from app.utils.exceptions import AppException, NotFoundError, AuthenticationError, AuthorizationError

logger = logging.getLogger(__name__)


async def _reservation_cleanup_loop():
    """Release expired marketplace listing reservations every 5 minutes."""
    from app.database import engine as async_engine
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession

    while True:
        try:
            await asyncio.sleep(300)  # 5 minutes
            async with AsyncSession(async_engine) as session:
                result = await session.execute(text("SELECT release_expired_reservations()"))
                await session.commit()
                released = result.scalar()
                if released:
                    logger.info(f"Released {released} expired reservation(s)")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Reservation cleanup error: {e}")


async def _abandoned_cart_email_loop():
    """Send abandoned cart emails for carts idle 2+ hours. Runs every 30 minutes."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select, update
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import selectinload
    from app.database import engine as async_engine
    from app.domain.models.cart import CartItem
    from app.domain.models.user import Customer
    from app.services.email_service import EmailService

    settings = get_settings()

    while True:
        try:
            await asyncio.sleep(1800)  # 30 minutes
            cutoff = datetime.now(timezone.utc) - timedelta(hours=2)

            async with AsyncSession(async_engine) as session:
                # Find users with cart items older than 2 hours that haven't been emailed
                result = await session.execute(
                    select(CartItem)
                    .options(selectinload(CartItem.product), selectinload(CartItem.user))
                    .where(
                        CartItem.updated_at < cutoff,
                        CartItem.abandoned_email_sent == False,
                    )
                )
                stale_items = list(result.scalars().all())

                if not stale_items:
                    continue

                # Group by user
                user_carts: dict[str, list] = {}
                for item in stale_items:
                    user_carts.setdefault(item.user_id, []).append(item)

                email_service = EmailService(
                    api_key=settings.zeptomail_api_key,
                    from_email=settings.zeptomail_from_email,
                    from_name=settings.zeptomail_from_name,
                    bounce_email=settings.zeptomail_bounce_email,
                    db=session,
                )

                for user_id, items in user_carts.items():
                    user = items[0].user
                    if not user or not user.email:
                        continue

                    cart_data = []
                    for ci in items:
                        if ci.product:
                            cart_data.append({
                                "name": ci.product.name,
                                "quantity": ci.quantity,
                                "price": ci.product.sell_price_zar,
                            })

                    if not cart_data:
                        continue

                    await email_service.send_abandoned_cart(
                        to_email=user.email,
                        to_name=user.name or user.first_name or "there",
                        cart_items=cart_data,
                        cart_url="https://www.elitetcg.co.za/cart",
                        user_id=user_id,
                    )

                    # Flag items so we don't re-send
                    item_ids = [ci.id for ci in items]
                    await session.execute(
                        update(CartItem)
                        .where(CartItem.id.in_(item_ids))
                        .values(abandoned_email_sent=True)
                    )

                await session.commit()
                sent_count = len(user_carts)
                if sent_count:
                    logger.info(f"[ABANDONED CART] Sent {sent_count} abandoned cart email(s)")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Abandoned cart email error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print("Elite TCG Microservice starting...")

    # Validate Payflex config on startup (warn if missing, don't crash)
    from app.payments.payflex.config import get_payflex_settings
    pf = get_payflex_settings()
    if pf.is_configured:
        print(f"Payflex: enabled (mode={pf.payflex_mode})")
    else:
        print("Payflex: DISABLED (missing credentials)")

    # Log card evaluation service status
    if settings.pokemon_tcg_api_key:
        print("Card Evaluation: enabled (pokemontcg.io API key set)")
    else:
        print("Card Evaluation: limited (no API key, 1k requests/day)")

    if settings.google_cloud_vision_api_key:
        print("Card Scanner: enabled (Google Cloud Vision)")
        print("Seller Verification: enabled (face detection + ID OCR)")
    else:
        print("Card Scanner: DISABLED (no Vision API key)")
        print("Seller Verification: DISABLED (requires Vision API key)")

    # Start background reservation cleanup
    cleanup_task = asyncio.create_task(_reservation_cleanup_loop())
    print("Marketplace: reservation cleanup started (every 5 min)")

    # Start abandoned cart email loop
    abandoned_cart_task = asyncio.create_task(_abandoned_cart_email_loop())
    print("Email: abandoned cart reminder started (every 30 min)")

    if settings.zeptomail_api_key:
        print(f"Email: ZeptoMail enabled (from={settings.zeptomail_from_email})")
    else:
        print("Email: ZeptoMail DISABLED (no API key)")

    yield

    cleanup_task.cancel()
    abandoned_cart_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    try:
        await abandoned_cart_task
    except asyncio.CancelledError:
        pass
    print("Shutting down...")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Elite TCG Microservice API",
        description="Payments, shipping, card evaluation, and marketplace services for Elite TCG",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.frontend_url,
            "https://elitetcg.co.za",
            "https://www.elitetcg.co.za",
        ],
        allow_origin_regex=r"http://localhost:\d+",
        allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api/v1")

    # Exception handlers for custom exceptions
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(status_code=401, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(AuthorizationError)
    async def authz_error_handler(request: Request, exc: AuthorizationError):
        return JSONResponse(status_code=403, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(status_code=400, content={"detail": exc.message, "code": exc.code})

    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "elite-tcg-microservice"}

    return app


app = create_app()

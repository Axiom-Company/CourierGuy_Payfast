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
    else:
        print("Card Scanner: DISABLED (no Vision API key)")

    # Start background reservation cleanup
    cleanup_task = asyncio.create_task(_reservation_cleanup_loop())
    print("Marketplace: reservation cleanup started (every 5 min)")

    yield

    cleanup_task.cancel()
    try:
        await cleanup_task
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

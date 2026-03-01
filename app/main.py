from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.config import get_settings
from app.api.router import api_router
from app.utils.exceptions import AppException, NotFoundError, AuthenticationError, AuthorizationError


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Elite TCG API starting...")

    # Validate Payflex config on startup (warn if missing, don't crash)
    from app.payments.payflex.config import get_payflex_settings
    pf = get_payflex_settings()
    if pf.is_configured:
        print(f"Payflex: enabled (mode={pf.payflex_mode})")
    else:
        print("Payflex: DISABLED (missing credentials)")

    yield
    print("Shutting down...")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Elite TCG Payments & Shipping API",
        description="PayFast payment processing and Courier Guy shipping microservice for Elite TCG",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
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
        return {"status": "ok", "service": "pokemon-card-store-api"}

    return app


app = create_app()

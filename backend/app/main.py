"""
Sajjad API — FastAPI application factory.

Startup/shutdown:
- Validates DB connection on startup
- Closes connection pool on shutdown

Middleware stack (outer → inner):
1. CORS
2. SlowAPI rate limiting
3. Request ID injection
4. Trusted host (prod only)
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.config import get_settings
from app.core.exceptions import (
    Conflict,
    DomainNotVerified,
    Forbidden,
    NotFound,
    PlanLimitExceeded,
    SajjadAPIError,
    ScanAlreadyRunning,
    Unauthorized,
)
from app.database import engine
from app.routers import auth, billing, domains, public, scans, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("sajjad.api")

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "Starting Sajjad API [%s]", settings.api_env
    )
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection OK")
    yield
    await engine.dispose()
    logger.info("Sajjad API shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Sajjad EASM API",
        description=(
            "External Attack Surface Management for Latin American SMEs. "
            "Monitor what attackers see about your company."
        ),
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Rate limiting ────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS ─────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Trusted hosts (production guard) ─────────────────
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["sajjad.app", "*.sajjad.app"],
        )

    # ── Request ID middleware ─────────────────────────────
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get(
            "X-Request-ID", str(uuid.uuid4())
        )
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed = time.perf_counter() - start
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed:.3f}s"
        return response

    # ── Exception handlers ───────────────────────────────
    @app.exception_handler(SajjadAPIError)
    async def handle_api_error(
        request: Request, exc: SajjadAPIError
    ):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred.",
            },
        )

    # ── Routers ───────────────────────────────────────────
    prefix = "/api/v1"
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(domains.router, prefix=prefix)
    app.include_router(scans.router, prefix=prefix)
    app.include_router(billing.router, prefix=prefix)
    app.include_router(public.router, prefix=prefix)

    # ── Health check ──────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok", "service": "sajjad-api"}

    return app


app = create_app()

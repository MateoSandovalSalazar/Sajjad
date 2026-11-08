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
from redis.asyncio import Redis
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import get_settings

# Un único handler cubre toda la jerarquía: Starlette recorre el MRO
# de la excepción al buscar handler, así que registrar la clase base
# atrapa a todas sus subclases.
from app.core.exceptions import SajjadAPIError
from app.core.observability import (
    configure_logging,
    configure_sentry,
    request_id_ctx,
)
from app.core.ratelimit import limiter
from app.database import engine
from app.routers import auth, billing, domains, scans, users

configure_logging()
configure_sentry()

logger = logging.getLogger("sajjad.api")


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

    @app.exception_handler(RateLimitExceeded)
    async def handle_rate_limit(request: Request, exc: RateLimitExceeded):
        """
        Devuelve el 429 en el mismo sobre JSON que el resto de errores
        ({"error", "message"}) en vez del formato propio de SlowAPI,
        para que el frontend lo traduzca por código como los demás.
        """
        logger.warning(
            "Rate limit alcanzado: %s %s desde %s",
            request.method,
            request.url.path,
            request.client.host if request.client else "desconocido",
        )
        response = JSONResponse(
            status_code=429,
            content={
                "error": "RateLimitExceeded",
                "message": (
                    "Demasiados intentos. Espera un momento y "
                    "vuelve a intentarlo."
                ),
            },
        )
        # Cabecera estándar para que los clientes sepan cuánto esperar.
        return request.app.state.limiter._inject_headers(
            response, request.state.view_rate_limit
        )

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
            allowed_hosts=settings.trusted_hosts,
        )

    # ── Request ID middleware ─────────────────────────────
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = request.headers.get(
            "X-Request-ID", str(uuid.uuid4())
        )
        # En un ContextVar para que el formatter lo adjunte a cada
        # línea de log de esta petición sin tener que pasarlo a mano
        # por toda la pila de llamadas.
        token = request_id_ctx.set(request_id)
        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        finally:
            elapsed = time.perf_counter() - start
            request_id_ctx.reset(token)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{elapsed:.3f}s"

        # Una línea de acceso por petición, con los campos que de
        # verdad se consultan al investigar un incidente.
        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(elapsed * 1000, 1),
                "client_ip": (
                    request.client.host if request.client else None
                ),
            },
        )
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

    # ── Health checks ─────────────────────────────────────
    # Se separan a propósito: el orquestador reinicia el contenedor
    # cuando /health falla, y lo saca del balanceador cuando falla
    # /health/ready. Una caída de Postgres no debe reiniciar la API
    # en bucle, sólo dejar de recibir tráfico.
    @app.get("/health", tags=["health"])
    async def health():
        """Liveness: el proceso responde."""
        return {"status": "ok", "service": "sajjad-api"}

    @app.get("/health/ready", tags=["health"])
    async def readiness():
        """Readiness: las dependencias externas contestan."""
        checks: dict[str, str] = {}

        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:
            logger.error("Readiness: database KO: %s", exc)
            checks["database"] = "error"

        try:
            redis = Redis.from_url(settings.redis_url)
            try:
                await redis.ping()
                checks["redis"] = "ok"
            finally:
                await redis.aclose()
        except Exception as exc:
            logger.error("Readiness: redis KO: %s", exc)
            checks["redis"] = "error"

        healthy = all(v == "ok" for v in checks.values())
        return JSONResponse(
            status_code=200 if healthy else 503,
            content={
                "status": "ok" if healthy else "degraded",
                "checks": checks,
            },
        )

    return app


app = create_app()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.config import validate_security
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.db.session import init_db
from app.middleware.correlation_id import CorrelationIDMiddleware
from app.middleware.rate_limiter import InMemoryRateLimiter
from app.middleware.request_tracer import RequestTracerMiddleware
from app.services.auth_service import ensure_bootstrap_admin
from app.services.document_service import ensure_document_storage


def create_application() -> FastAPI:
    configure_logging(
        level="INFO",
        json_logs=(settings.app_env != "development"),
    )

    # Refuse to start with an insecure configuration in production.
    security_problems = validate_security(settings)
    if security_problems:
        raise RuntimeError(
            "Insecure production configuration: " + "; ".join(security_problems)
        )

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Production-grade automotive insurance claim orchestration platform. "
            "Supports end-to-end claim lifecycle, fraud detection, adjuster assignment, "
            "repair estimation, payout settlement, and real-time event publishing."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "Claims Engineering",
            "email": "claims-engineering@example.com",
        },
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0",
        },
    )

    # Middleware stack (outermost first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID", "X-Request-ID", "X-RateLimit-Remaining"],
    )
    app.add_middleware(InMemoryRateLimiter, default_limit=200, auth_limit=20)
    app.add_middleware(RequestTracerMiddleware)
    app.add_middleware(CorrelationIDMiddleware)

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    def on_startup() -> None:
        ensure_document_storage()
        init_db()
        session = SessionLocal()
        try:
            ensure_bootstrap_admin(session)
        finally:
            session.close()

    return app


app = create_application()

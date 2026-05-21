from fastapi import FastAPI

from app.api.routes import router as api_router
from app.core.config import settings
from app.db.session import init_db
from app.services.document_service import ensure_document_storage


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    def on_startup() -> None:
        ensure_document_storage()
        init_db()

    return app


app = create_application()

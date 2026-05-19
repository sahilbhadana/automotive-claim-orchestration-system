from fastapi import APIRouter

from app.api.claim_routes import router as claim_router
from app.core.config import settings
from app.db.session import check_database_connection

router = APIRouter()
router.include_router(claim_router)


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@router.get("/ready")
async def readiness() -> dict[str, str]:
    database_status = "up" if check_database_connection() else "down"
    overall_status = "ready" if database_status == "up" else "degraded"
    return {
        "status": overall_status,
        "database": database_status,
    }

from fastapi import APIRouter

from app.api.adjuster_routes import router as adjuster_router
from app.api.audit_routes import router as audit_router
from app.api.auth_routes import router as auth_router
from app.api.claim_routes import router as claim_router
from app.api.document_routes import router as document_router
from app.api.fraud_routes import router as fraud_router
from app.api.garage_routes import router as garage_router
from app.api.metrics_routes import router as metrics_router
from app.api.notification_routes import router as notification_router
from app.api.policy_routes import router as policy_router
from app.api.retry_routes import router as retry_router
from app.api.settlement_routes import router as settlement_router
from app.api.survey_routes import router as survey_router
from app.api.task_routes import router as task_router
from app.api.verification_routes import router as verification_router
from app.api.workflow_routes import router as workflow_router
from app.core.config import settings
from app.db.session import check_database_connection

router = APIRouter()
router.include_router(adjuster_router)
router.include_router(audit_router)
router.include_router(auth_router)
router.include_router(claim_router)
router.include_router(document_router)
router.include_router(fraud_router)
router.include_router(garage_router)
router.include_router(metrics_router)
router.include_router(notification_router)
router.include_router(policy_router)
router.include_router(retry_router)
router.include_router(settlement_router)
router.include_router(survey_router)
router.include_router(task_router)
router.include_router(verification_router)
router.include_router(workflow_router)


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

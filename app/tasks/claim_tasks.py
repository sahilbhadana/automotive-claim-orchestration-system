from __future__ import annotations

from uuid import UUID

from app.db.session import SessionLocal
from app.models.claim import ClaimStatus
from app.models.document import DocumentType
from app.services.claim_service import get_claim_by_id
from app.services.document_service import list_claim_documents
from app.services.policy_service import get_policy_by_number
from app.services.workflow_service import build_workflow_transition_name
from app.services.workflow_service import execute_workflow_step
from app.workers.celery_app import celery_app


@celery_app.task(name="claims.validate_images")
def validate_claim_images_task(claim_id: str) -> dict:
    session = SessionLocal()
    try:
        claim_uuid = UUID(claim_id)
        claim = get_claim_by_id(session, claim_uuid)
        if claim is None:
            return {"claim_id": claim_id, "valid": False, "reasons": ["Claim not found"]}

        documents = list_claim_documents(session, claim_uuid)
        accident_photos = [
            document
            for document in documents
            if document.document_type == DocumentType.ACCIDENT_PHOTO
        ]

        reasons: list[str] = []
        if not accident_photos:
            reasons.append("No accident photos uploaded")

        for document in accident_photos:
            if document.content_type not in {"image/jpeg", "image/png", "image/webp"}:
                reasons.append(
                    f"Unsupported accident photo type detected: {document.content_type}"
                )

        return {
            "claim_id": claim_id,
            "valid": not reasons,
            "photo_count": len(accident_photos),
            "reasons": reasons,
        }
    finally:
        session.close()


@celery_app.task(name="claims.run_fraud_checks")
def run_claim_fraud_checks_task(claim_id: str) -> dict:
    session = SessionLocal()
    try:
        claim_uuid = UUID(claim_id)
        claim = get_claim_by_id(session, claim_uuid)
        if claim is None:
            return {"claim_id": claim_id, "risk_level": "UNKNOWN", "flags": ["Claim not found"]}

        documents = list_claim_documents(session, claim_uuid)
        policy = get_policy_by_number(session, claim.policy_number)

        flags: list[str] = []
        risk_score = 0

        if float(claim.claim_amount) >= 250000:
            flags.append("High claim amount")
            risk_score += 2

        if not any(document.document_type == DocumentType.FIR for document in documents):
            flags.append("FIR document missing")
            risk_score += 2

        if len(documents) < 2:
            flags.append("Insufficient supporting evidence")
            risk_score += 1

        if policy is None:
            flags.append("Policy not found during fraud screening")
            risk_score += 2

        risk_level = "LOW"
        if risk_score >= 4:
            risk_level = "HIGH"
        elif risk_score >= 2:
            risk_level = "MEDIUM"

        return {
            "claim_id": claim_id,
            "risk_level": risk_level,
            "flags": flags,
        }
    finally:
        session.close()


@celery_app.task(name="claims.send_notification")
def send_claim_notification_task(claim_id: str, message: str) -> dict:
    session = SessionLocal()
    try:
        claim_uuid = UUID(claim_id)
        claim = get_claim_by_id(session, claim_uuid)
        if claim is None:
            return {
                "claim_id": claim_id,
                "delivered": False,
                "channel": "email",
                "message": "Claim not found",
            }

        return {
            "claim_id": claim_id,
            "delivered": True,
            "channel": "email",
            "message": message,
            "claim_status": claim.status.value,
        }
    finally:
        session.close()


@celery_app.task(name="claims.execute_workflow_step")
def execute_workflow_step_task(
    claim_id: str,
    target_status: str | None = None,
    reason: str | None = None,
) -> dict:
    session = SessionLocal()
    try:
        claim_uuid = UUID(claim_id)
        claim = get_claim_by_id(session, claim_uuid)
        if claim is None:
            return {
                "claim_id": claim_id,
                "executed": False,
                "error": "Claim not found",
            }

        resolved_target = ClaimStatus(target_status) if target_status is not None else None
        previous_status, updated_claim = execute_workflow_step(
            session=session,
            claim=claim,
            target_status=resolved_target,
        )

        follow_up_tasks: list[str] = []

        if updated_claim.status == ClaimStatus.DOCUMENT_VERIFICATION:
            validate_claim_images_task.delay(claim_id)
            follow_up_tasks.append("claims.validate_images")

        if updated_claim.status == ClaimStatus.FRAUD_ANALYSIS:
            run_claim_fraud_checks_task.delay(claim_id)
            follow_up_tasks.append("claims.run_fraud_checks")

        if updated_claim.status in {
            ClaimStatus.APPROVED,
            ClaimStatus.REJECTED,
            ClaimStatus.PAYOUT,
        }:
            notification_message = reason or f"Claim moved to {updated_claim.status.value}"
            send_claim_notification_task.delay(claim_id, notification_message)
            follow_up_tasks.append("claims.send_notification")

        return {
            "claim_id": claim_id,
            "executed": True,
            "previous_status": previous_status.value,
            "current_status": updated_claim.status.value,
            "transition": build_workflow_transition_name(previous_status, updated_claim.status),
            "follow_up_tasks": follow_up_tasks,
        }
    finally:
        session.close()

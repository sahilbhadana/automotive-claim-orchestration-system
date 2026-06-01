from __future__ import annotations

from uuid import UUID

from app.db.session import SessionLocal
from app.models.claim import ClaimStatus
from app.models.document import DocumentType
from app.services.adjuster_service import assign_best_adjuster
from app.services.adjuster_service import determine_required_expertise
from app.services.claim_service import get_claim_by_id
from app.services.document_service import list_claim_documents
from app.services.fraud_service import analyze_claim_for_fraud
from app.services.garage_service import approve_repair_estimate
from app.services.garage_service import get_repair_estimate_by_id
from app.services.notification_service import dispatch_claim_notification
from app.services.policy_service import get_policy_by_number
from app.services.workflow_service import build_workflow_transition_name
from app.services.workflow_service import execute_workflow_step
from app.workers.celery_app import celery_app
from app.schemas.fraud import FraudCheckRequest
from app.schemas.garage import RepairEstimateApprovalRequest


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
def run_claim_fraud_checks_task(
    claim_id: str,
    garage_name: str | None = None,
    repair_estimate_amount: float | None = None,
) -> dict:
    session = SessionLocal()
    try:
        claim_uuid = UUID(claim_id)
        claim = get_claim_by_id(session, claim_uuid)
        if claim is None:
            return {
                "claim_id": claim_id,
                "risk_level": "UNKNOWN",
                "risk_score": 0,
                "triggered_rules": ["claim_not_found"],
            }

        analysis = analyze_claim_for_fraud(
            session=session,
            claim=claim,
            payload=None
            if garage_name is None and repair_estimate_amount is None
            else FraudCheckRequest(
                garage_name=garage_name,
                repair_estimate_amount=repair_estimate_amount,
            ),
        ).model_dump()

        documents = list_claim_documents(session, claim_uuid)
        policy = get_policy_by_number(session, claim.policy_number)

        if not any(document.document_type == DocumentType.FIR for document in documents):
            analysis["triggered_rules"].append("missing_fir_document")
            analysis["risk_score"] += 2

        if len(documents) < 2:
            analysis["triggered_rules"].append("insufficient_supporting_evidence")
            analysis["risk_score"] += 1

        if policy is None:
            analysis["triggered_rules"].append("policy_missing_during_fraud_screening")
            analysis["risk_score"] += 2

        analysis["risk_level"] = resolve_risk_level(analysis["risk_score"])
        return analysis
    finally:
        session.close()


@celery_app.task(name="claims.send_notification")
def send_claim_notification_task(
    claim_id: str,
    event_name: str,
    message: str | None = None,
    previous_status: str | None = None,
    adjuster_name: str | None = None,
) -> dict:
    session = SessionLocal()
    try:
        claim_uuid = UUID(claim_id)
        claim = get_claim_by_id(session, claim_uuid)
        if claim is None:
            return {
                "claim_id": claim_id,
                "delivered": False,
                "event_name": event_name,
                "deliveries": [],
                "message": "Claim not found",
            }

        return dispatch_claim_notification(
            session=session,
            claim=claim,
            event_name=event_name,
            previous_status=previous_status,
            adjuster_name=adjuster_name,
            override_message=message,
        )
    finally:
        session.close()


@celery_app.task(name="claims.assign_adjuster")
def assign_adjuster_task(claim_id: str) -> dict:
    session = SessionLocal()
    try:
        claim_uuid = UUID(claim_id)
        claim = get_claim_by_id(session, claim_uuid)
        if claim is None:
            return {
                "claim_id": claim_id,
                "assigned": False,
                "error": "Claim not found",
            }

        ranked = assign_best_adjuster(session, claim)
        send_claim_notification_task.delay(
            claim_id,
            "adjuster_assigned",
            None,
            None,
            ranked.adjuster.full_name,
        )
        return {
            "claim_id": claim_id,
            "assigned": True,
            "adjuster_id": str(ranked.adjuster.id),
            "adjuster_name": ranked.adjuster.full_name,
            "city_match": ranked.city_match,
            "required_expertise": determine_required_expertise(float(claim.claim_amount)).value,
            "assigned_expertise": ranked.adjuster.expertise.value,
        }
    except Exception as exc:
        return {
            "claim_id": claim_id,
            "assigned": False,
            "error": str(exc),
        }
    finally:
        session.close()


@celery_app.task(name="claims.approve_repair_estimate")
def approve_repair_estimate_task(
    estimate_id: str,
    approved: bool,
    approval_notes: str | None = None,
) -> dict:
    session = SessionLocal()
    try:
        estimate_uuid = UUID(estimate_id)
        estimate = get_repair_estimate_by_id(session, estimate_uuid)
        if estimate is None:
            return {
                "estimate_id": estimate_id,
                "updated": False,
                "error": "Repair estimate not found",
            }

        updated_estimate = approve_repair_estimate(
            session=session,
            estimate=estimate,
            payload=RepairEstimateApprovalRequest(
                approved=approved,
                approval_notes=approval_notes,
            ),
        )
        return {
            "estimate_id": estimate_id,
            "updated": True,
            "status": updated_estimate.status.value,
            "claim_id": str(updated_estimate.claim_id),
        }
    except Exception as exc:
        return {
            "estimate_id": estimate_id,
            "updated": False,
            "error": str(exc),
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

        if updated_claim.status == ClaimStatus.ADJUSTER_ASSIGNMENT:
            assign_adjuster_task.delay(claim_id)
            follow_up_tasks.append("claims.assign_adjuster")

        if updated_claim.status in {
            ClaimStatus.APPROVED,
            ClaimStatus.REJECTED,
            ClaimStatus.PAYOUT,
        }:
            send_claim_notification_task.delay(
                claim_id,
                "workflow_transition",
                reason,
                previous_status.value,
            )
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


def resolve_risk_level(risk_score: int) -> str:
    if risk_score >= 6:
        return "HIGH"
    if risk_score >= 3:
        return "MEDIUM"
    return "LOW"

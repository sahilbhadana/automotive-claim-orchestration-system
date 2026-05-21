from uuid import UUID

from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.claim import ClaimStatus
from app.services.claim_service import update_claim_status

DEFAULT_WORKFLOW_TRANSITIONS: dict[ClaimStatus, list[ClaimStatus]] = {
    ClaimStatus.CLAIM_CREATED: [ClaimStatus.DOCUMENT_VERIFICATION],
    ClaimStatus.DOCUMENT_VERIFICATION: [ClaimStatus.POLICY_VALIDATION, ClaimStatus.REJECTED],
    ClaimStatus.POLICY_VALIDATION: [ClaimStatus.FRAUD_ANALYSIS, ClaimStatus.REJECTED],
    ClaimStatus.FRAUD_ANALYSIS: [ClaimStatus.ADJUSTER_ASSIGNMENT, ClaimStatus.REJECTED],
    ClaimStatus.ADJUSTER_ASSIGNMENT: [ClaimStatus.REPAIR_ESTIMATION],
    ClaimStatus.REPAIR_ESTIMATION: [ClaimStatus.FINAL_APPROVAL, ClaimStatus.REJECTED],
    ClaimStatus.FINAL_APPROVAL: [ClaimStatus.APPROVED, ClaimStatus.REJECTED],
    ClaimStatus.APPROVED: [ClaimStatus.PAYOUT],
    ClaimStatus.REJECTED: [],
    ClaimStatus.PAYOUT: [],
}


class WorkflowTransitionError(ValueError):
    pass


def get_allowed_transitions(current_status: ClaimStatus) -> list[ClaimStatus]:
    return DEFAULT_WORKFLOW_TRANSITIONS.get(current_status, [])


def is_terminal_state(current_status: ClaimStatus) -> bool:
    return not get_allowed_transitions(current_status)


def execute_workflow_step(
    session: Session,
    claim: Claim,
    target_status: ClaimStatus | None = None,
) -> tuple[ClaimStatus, Claim]:
    previous_status = claim.status
    allowed_transitions = get_allowed_transitions(previous_status)

    if not allowed_transitions:
        raise WorkflowTransitionError(
            f"Claim is already in terminal workflow state {previous_status}"
        )

    resolved_target = resolve_target_status(
        allowed_transitions=allowed_transitions,
        target_status=target_status,
    )

    updated_claim = update_claim_status(session, claim, resolved_target)
    return previous_status, updated_claim


def resolve_target_status(
    allowed_transitions: list[ClaimStatus],
    target_status: ClaimStatus | None,
) -> ClaimStatus:
    if target_status is None:
        if len(allowed_transitions) != 1:
            raise WorkflowTransitionError(
                "Multiple transition paths available; target_status is required"
            )
        return allowed_transitions[0]

    if target_status not in allowed_transitions:
        allowed = ", ".join(status.value for status in allowed_transitions)
        raise WorkflowTransitionError(
            f"Transition to {target_status} is not allowed from current state. Allowed: {allowed}"
        )

    return target_status


def build_workflow_transition_name(
    previous_status: ClaimStatus,
    current_status: ClaimStatus,
) -> str:
    return f"{previous_status}->{current_status}"


def serialize_claim_id(claim_id: UUID) -> str:
    return str(claim_id)

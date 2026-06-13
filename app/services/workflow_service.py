from uuid import UUID

from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.claim import ClaimStatus
from app.models.claim import ClaimType
from app.services.audit_service import record_audit_event
from app.services.claim_service import update_claim_status

# Own-damage path (accident / natural disaster): the full manual —
# surveyor appointed, vehicle inspected before repairs, estimate,
# survey report, then approval and payout.
OWN_DAMAGE_TRANSITIONS: dict[ClaimStatus, list[ClaimStatus]] = {
    ClaimStatus.CLAIM_CREATED: [ClaimStatus.DOCUMENT_VERIFICATION],
    ClaimStatus.DOCUMENT_VERIFICATION: [
        ClaimStatus.POLICY_VALIDATION,
        ClaimStatus.REJECTED,
    ],
    ClaimStatus.POLICY_VALIDATION: [ClaimStatus.FRAUD_ANALYSIS, ClaimStatus.REJECTED],
    ClaimStatus.FRAUD_ANALYSIS: [ClaimStatus.ADJUSTER_ASSIGNMENT, ClaimStatus.REJECTED],
    ClaimStatus.ADJUSTER_ASSIGNMENT: [ClaimStatus.VEHICLE_INSPECTION],
    ClaimStatus.VEHICLE_INSPECTION: [
        ClaimStatus.REPAIR_ESTIMATION,
        ClaimStatus.REJECTED,
    ],
    ClaimStatus.REPAIR_ESTIMATION: [
        ClaimStatus.SURVEY_REPORT_REVIEW,
        ClaimStatus.REJECTED,
    ],
    ClaimStatus.SURVEY_REPORT_REVIEW: [
        ClaimStatus.FINAL_APPROVAL,
        ClaimStatus.REJECTED,
    ],
    ClaimStatus.FINAL_APPROVAL: [ClaimStatus.APPROVED, ClaimStatus.REJECTED],
    ClaimStatus.APPROVED: [ClaimStatus.PAYOUT],
    ClaimStatus.REJECTED: [],
    ClaimStatus.PAYOUT: [],
}

# Theft: no vehicle to inspect or repair. An investigator verifies the
# facts (FIR, non-traceable report), reports, and the claim settles at
# the vehicle's IDV.
THEFT_TRANSITIONS: dict[ClaimStatus, list[ClaimStatus]] = {
    ClaimStatus.CLAIM_CREATED: [ClaimStatus.DOCUMENT_VERIFICATION],
    ClaimStatus.DOCUMENT_VERIFICATION: [
        ClaimStatus.POLICY_VALIDATION,
        ClaimStatus.REJECTED,
    ],
    ClaimStatus.POLICY_VALIDATION: [ClaimStatus.FRAUD_ANALYSIS, ClaimStatus.REJECTED],
    ClaimStatus.FRAUD_ANALYSIS: [ClaimStatus.ADJUSTER_ASSIGNMENT, ClaimStatus.REJECTED],
    ClaimStatus.ADJUSTER_ASSIGNMENT: [ClaimStatus.SURVEY_REPORT_REVIEW],
    ClaimStatus.SURVEY_REPORT_REVIEW: [
        ClaimStatus.FINAL_APPROVAL,
        ClaimStatus.REJECTED,
    ],
    ClaimStatus.FINAL_APPROVAL: [ClaimStatus.APPROVED, ClaimStatus.REJECTED],
    ClaimStatus.APPROVED: [ClaimStatus.PAYOUT],
    ClaimStatus.REJECTED: [],
    ClaimStatus.PAYOUT: [],
}

# Third-party: liability is decided by the Motor Accident Claims
# Tribunal after legal review — no surveyor estimate of our own vehicle.
THIRD_PARTY_TRANSITIONS: dict[ClaimStatus, list[ClaimStatus]] = {
    ClaimStatus.CLAIM_CREATED: [ClaimStatus.DOCUMENT_VERIFICATION],
    ClaimStatus.DOCUMENT_VERIFICATION: [
        ClaimStatus.POLICY_VALIDATION,
        ClaimStatus.REJECTED,
    ],
    ClaimStatus.POLICY_VALIDATION: [ClaimStatus.LEGAL_REVIEW, ClaimStatus.REJECTED],
    ClaimStatus.LEGAL_REVIEW: [ClaimStatus.FINAL_APPROVAL, ClaimStatus.REJECTED],
    ClaimStatus.FINAL_APPROVAL: [ClaimStatus.APPROVED, ClaimStatus.REJECTED],
    ClaimStatus.APPROVED: [ClaimStatus.PAYOUT],
    ClaimStatus.REJECTED: [],
    ClaimStatus.PAYOUT: [],
}

WORKFLOW_TRANSITIONS_BY_TYPE: dict[ClaimType, dict[ClaimStatus, list[ClaimStatus]]] = {
    ClaimType.ACCIDENT: OWN_DAMAGE_TRANSITIONS,
    ClaimType.NATURAL_DISASTER: OWN_DAMAGE_TRANSITIONS,
    ClaimType.THEFT: THEFT_TRANSITIONS,
    ClaimType.THIRD_PARTY: THIRD_PARTY_TRANSITIONS,
}

# Backwards-compatible default used when no claim type is supplied.
DEFAULT_WORKFLOW_TRANSITIONS = OWN_DAMAGE_TRANSITIONS


class WorkflowTransitionError(ValueError):
    pass


def get_allowed_transitions(
    current_status: ClaimStatus,
    claim_type: ClaimType | None = None,
) -> list[ClaimStatus]:
    transitions = WORKFLOW_TRANSITIONS_BY_TYPE.get(
        claim_type or ClaimType.ACCIDENT, DEFAULT_WORKFLOW_TRANSITIONS
    )
    return transitions.get(current_status, [])


def is_terminal_state(
    current_status: ClaimStatus,
    claim_type: ClaimType | None = None,
) -> bool:
    return not get_allowed_transitions(current_status, claim_type)


def _enforce_procedural_requirements(
    session: Session,
    claim: Claim,
    target: ClaimStatus,
) -> None:
    """Guards from the claims manual: documents before verification
    passes, a surveyor before inspection, an inspection before repairs
    are authorized, and a submitted report before it can be reviewed."""
    from app.services.document_service import list_claim_documents
    from app.services.survey_service import get_survey_for_claim

    if (
        claim.status == ClaimStatus.DOCUMENT_VERIFICATION
        and target == ClaimStatus.POLICY_VALIDATION
    ):
        if not list_claim_documents(session, claim.id):
            raise WorkflowTransitionError(
                "At least one supporting document must be uploaded before "
                "document verification can pass"
            )

    if target == ClaimStatus.VEHICLE_INSPECTION:
        if get_survey_for_claim(session, claim.id) is None:
            raise WorkflowTransitionError(
                "A surveyor must be appointed before the vehicle inspection stage"
            )

    if target == ClaimStatus.REPAIR_ESTIMATION:
        survey = get_survey_for_claim(session, claim.id)
        if survey is None or survey.inspected_at is None:
            raise WorkflowTransitionError(
                "Repairs cannot be authorized until the surveyor has "
                "inspected the vehicle"
            )

    if target == ClaimStatus.SURVEY_REPORT_REVIEW:
        survey = get_survey_for_claim(session, claim.id)
        if survey is None or survey.report_submitted_at is None:
            raise WorkflowTransitionError(
                "The survey report must be submitted before it can be reviewed"
            )


def execute_workflow_step(
    session: Session,
    claim: Claim,
    target_status: ClaimStatus | None = None,
) -> tuple[ClaimStatus, Claim]:
    previous_status = claim.status
    allowed_transitions = get_allowed_transitions(previous_status, claim.claim_type)

    if not allowed_transitions:
        raise WorkflowTransitionError(
            f"Claim is already in terminal workflow state {previous_status}"
        )

    resolved_target = resolve_target_status(
        allowed_transitions=allowed_transitions,
        target_status=target_status,
    )

    _enforce_procedural_requirements(session, claim, resolved_target)

    updated_claim = update_claim_status(session, claim, resolved_target)
    record_audit_event(
        session,
        entity_type="workflow",
        entity_id=str(updated_claim.id),
        claim_id=updated_claim.id,
        action="WORKFLOW_TRANSITION_EXECUTED",
        details={
            "previous_status": previous_status.value,
            "current_status": updated_claim.status.value,
            "claim_type": claim.claim_type.value if claim.claim_type else None,
            "transition": build_workflow_transition_name(
                previous_status, updated_claim.status
            ),
        },
    )
    session.commit()
    session.refresh(updated_claim)
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

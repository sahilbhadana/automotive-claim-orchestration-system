from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.policy import CoverageType
from app.models.policy import Policy
from app.models.policy import PolicyStatus
from app.schemas.policy import PolicyCreate
from app.schemas.policy import PolicyValidationRequest
from app.schemas.policy import PolicyValidationResult


def create_policy(session: Session, payload: PolicyCreate) -> Policy:
    policy = Policy(**payload.model_dump())
    session.add(policy)
    session.commit()
    session.refresh(policy)
    return policy


def list_policies(session: Session) -> list[Policy]:
    statement = select(Policy).order_by(Policy.created_at.desc())
    return list(session.scalars(statement).all())


def get_policy_by_number(session: Session, policy_number: str) -> Policy | None:
    statement = select(Policy).where(Policy.policy_number == policy_number)
    return session.scalar(statement)


def validate_policy_coverage(
    policy: Policy | None,
    payload: PolicyValidationRequest,
) -> PolicyValidationResult:
    if policy is None:
        return PolicyValidationResult(
            policy_number=payload.policy_number,
            eligible=False,
            status=None,
            coverage_type=None,
            vehicle_match=False,
            reasons=["Policy not found"],
        )

    reasons: list[str] = []
    vehicle_match = policy.vehicle_number == payload.vehicle_number

    if not vehicle_match:
        reasons.append("Vehicle is not insured under this policy")

    if policy.status != PolicyStatus.ACTIVE:
        reasons.append(f"Policy is not active: {policy.status}")

    if policy.expiry_date < payload.incident_date:
        reasons.append("Policy expired before the incident date")

    if policy.effective_date > payload.incident_date:
        reasons.append("Policy was not yet effective on the incident date")

    if not policy.is_vehicle_insured:
        reasons.append("Vehicle coverage is disabled for this policy")

    if not coverage_satisfies_requirement(
        actual=policy.coverage_type,
        required=payload.required_coverage_type,
    ):
        reasons.append(
            f"Coverage type {policy.coverage_type} does not satisfy {payload.required_coverage_type}"
        )

    return PolicyValidationResult(
        policy_number=policy.policy_number,
        eligible=not reasons,
        status=policy.status,
        coverage_type=policy.coverage_type,
        vehicle_match=vehicle_match,
        reasons=reasons,
    )


def coverage_satisfies_requirement(
    actual: CoverageType,
    required: CoverageType,
) -> bool:
    coverage_rank = {
        CoverageType.THIRD_PARTY: 1,
        CoverageType.OWN_DAMAGE: 2,
        CoverageType.COMPREHENSIVE: 3,
    }
    return coverage_rank[actual] >= coverage_rank[required]

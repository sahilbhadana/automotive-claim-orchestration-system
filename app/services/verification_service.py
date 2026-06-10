import re

from app.models.policy import Policy
from app.schemas.verification import VerificationRequest
from app.schemas.verification import VerificationResult

VEHICLE_REGISTRATION_PATTERN = re.compile(r"^[A-Z]{2}\d{2}[A-Z]{1,3}\d{4}$")
DRIVING_LICENSE_PATTERN = re.compile(r"^[A-Z]{2}\d{2}\d{11}$")


def verify_vehicle_and_driver(
    policy: Policy | None,
    payload: VerificationRequest,
) -> VerificationResult:
    reasons: list[str] = []
    registration_number = normalize_identifier(payload.registration_number)
    vehicle_number = normalize_identifier(payload.vehicle_number)
    driving_license_number = normalize_identifier(payload.driving_license_number)

    vehicle_registration_valid = bool(
        VEHICLE_REGISTRATION_PATTERN.fullmatch(registration_number)
    )
    if not vehicle_registration_valid:
        reasons.append("Vehicle registration number format is invalid")

    driving_license_valid = bool(
        DRIVING_LICENSE_PATTERN.fullmatch(driving_license_number)
    )
    if not driving_license_valid:
        reasons.append("Driving license number format is invalid")

    if policy is None:
        reasons.append("Policy not found for verification")
        return VerificationResult(
            policy_number=payload.policy_number,
            vehicle_registration_valid=vehicle_registration_valid,
            driving_license_valid=driving_license_valid,
            owner_matches_policy=False,
            insured_vehicle_match=False,
            verification_passed=False,
            reasons=reasons,
        )

    insured_vehicle_match = (
        normalize_identifier(policy.vehicle_number) == vehicle_number
    )
    if not insured_vehicle_match:
        reasons.append("Vehicle does not match the insured policy vehicle")

    owner_matches_policy = normalize_name(policy.insured_name) == normalize_name(
        payload.owner_name
    )
    if not owner_matches_policy:
        reasons.append("Owner name does not match the insured party on the policy")

    verification_passed = (
        vehicle_registration_valid
        and driving_license_valid
        and insured_vehicle_match
        and owner_matches_policy
    )

    return VerificationResult(
        policy_number=payload.policy_number,
        vehicle_registration_valid=vehicle_registration_valid,
        driving_license_valid=driving_license_valid,
        owner_matches_policy=owner_matches_policy,
        insured_vehicle_match=insured_vehicle_match,
        verification_passed=verification_passed,
        reasons=reasons,
    )


def normalize_identifier(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def normalize_name(value: str) -> str:
    collapsed = " ".join(value.strip().upper().split())
    return collapsed

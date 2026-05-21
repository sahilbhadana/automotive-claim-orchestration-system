from pydantic import BaseModel
from pydantic import Field


class VerificationRequest(BaseModel):
    policy_number: str = Field(min_length=3, max_length=50)
    vehicle_number: str = Field(min_length=3, max_length=20)
    registration_number: str = Field(min_length=6, max_length=20)
    owner_name: str = Field(min_length=2, max_length=120)
    driver_name: str = Field(min_length=2, max_length=120)
    driving_license_number: str = Field(min_length=10, max_length=20)


class VerificationResult(BaseModel):
    policy_number: str
    vehicle_registration_valid: bool
    driving_license_valid: bool
    owner_matches_policy: bool
    insured_vehicle_match: bool
    verification_passed: bool
    reasons: list[str]

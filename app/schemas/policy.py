from datetime import date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.models.policy import CoverageType
from app.models.policy import PolicyStatus


class PolicyCreate(BaseModel):
    policy_number: str = Field(min_length=3, max_length=50)
    insured_name: str = Field(min_length=2, max_length=120)
    vehicle_number: str = Field(min_length=3, max_length=20)
    coverage_type: CoverageType
    status: PolicyStatus = PolicyStatus.ACTIVE
    effective_date: date
    expiry_date: date
    is_vehicle_insured: bool = True


class PolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_number: str
    insured_name: str
    vehicle_number: str
    coverage_type: CoverageType
    status: PolicyStatus
    effective_date: date
    expiry_date: date
    is_vehicle_insured: bool
    created_at: datetime
    updated_at: datetime


class PolicyValidationRequest(BaseModel):
    policy_number: str = Field(min_length=3, max_length=50)
    vehicle_number: str = Field(min_length=3, max_length=20)
    required_coverage_type: CoverageType
    incident_date: date


class PolicyValidationResult(BaseModel):
    policy_number: str
    eligible: bool
    status: PolicyStatus | None
    coverage_type: CoverageType | None
    vehicle_match: bool
    reasons: list[str]

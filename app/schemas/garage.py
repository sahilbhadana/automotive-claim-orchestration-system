from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.models.repair_estimate import RepairEstimateStatus


class GarageCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=100)
    specialization: str = Field(min_length=2, max_length=100)
    is_high_risk: bool = False
    is_active: bool = True


class GarageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    city: str
    specialization: str
    is_high_risk: bool
    is_active: bool
    created_at: datetime


class RepairEstimateCreate(BaseModel):
    garage_id: UUID
    estimated_amount: float = Field(gt=0)
    notes: str = Field(min_length=5, max_length=1000)


class RepairEstimateApprovalRequest(BaseModel):
    approved: bool
    approval_notes: str | None = Field(default=None, max_length=500)


class RepairEstimateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    claim_id: UUID
    garage_id: UUID
    estimated_amount: float
    notes: str
    status: RepairEstimateStatus
    approval_notes: str | None
    created_at: datetime
    updated_at: datetime

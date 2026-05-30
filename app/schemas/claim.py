from datetime import date
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.models.claim import ClaimStatus


class ClaimCreate(BaseModel):
    policy_number: str = Field(min_length=3, max_length=50)
    vehicle_number: str = Field(min_length=3, max_length=20)
    incident_date: date
    incident_city: str = Field(min_length=2, max_length=100)
    claim_amount: float = Field(gt=0)
    description: str = Field(min_length=10, max_length=1000)


class ClaimStatusUpdate(BaseModel):
    status: ClaimStatus


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    policy_number: str
    vehicle_number: str
    incident_date: date
    incident_city: str
    claim_amount: float
    description: str
    adjuster_id: UUID | None = None
    status: ClaimStatus
    created_at: datetime
    updated_at: datetime

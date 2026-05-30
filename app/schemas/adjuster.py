from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.models.adjuster import AdjusterExpertise


class AdjusterCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=100)
    expertise: AdjusterExpertise
    max_active_claims: int = Field(default=10, ge=1, le=100)
    is_active: bool = True


class AdjusterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    city: str
    expertise: AdjusterExpertise
    max_active_claims: int
    is_active: bool
    created_at: datetime


class AdjusterAssignmentRead(BaseModel):
    claim_id: UUID
    adjuster_id: UUID
    adjuster_name: str
    city_match: bool
    workload_count: int
    max_active_claims: int
    required_expertise: AdjusterExpertise
    assigned_expertise: AdjusterExpertise

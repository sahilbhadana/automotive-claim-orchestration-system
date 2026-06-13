from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.models.survey import InspectionMode
from app.models.survey import SurveyRecommendation
from app.models.survey import SurveyStatus


class SurveyAppointRequest(BaseModel):
    surveyor_name: str = Field(min_length=2, max_length=120)


class SurveyInspectionRequest(BaseModel):
    inspection_mode: InspectionMode
    notes: str | None = Field(default=None, max_length=2000)


class SurveyReportRequest(BaseModel):
    estimated_loss_amount: float = Field(gt=0)
    recommended_amount: float = Field(gt=0)
    recommendation: SurveyRecommendation
    notes: str | None = Field(default=None, max_length=2000)


class SurveyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    claim_id: UUID
    surveyor_name: str
    status: SurveyStatus
    inspection_mode: InspectionMode | None
    inspection_notes: str | None
    estimated_loss_amount: float | None
    recommended_amount: float | None
    recommendation: SurveyRecommendation | None
    report_notes: str | None
    appointed_at: datetime
    inspected_at: datetime | None
    report_submitted_at: datetime | None
    report_due_at: datetime | None
    report_overdue: bool = False

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel
from pydantic import Field


class FraudRecommendation(StrEnum):
    """The decision-support call returned to the insurer."""

    CLEAR = "CLEAR"  # looks legitimate — safe to proceed
    REVIEW = "REVIEW"  # some signals — manual review advised
    INVESTIGATE = "INVESTIGATE"  # strong signals — refer to investigation


class FraudCheckRequest(BaseModel):
    garage_name: str | None = Field(default=None, min_length=2, max_length=120)
    repair_estimate_amount: float | None = Field(default=None, gt=0)


class FraudSignal(BaseModel):
    """One row of the scoring matrix."""

    code: str
    label: str
    weight: int
    triggered: bool
    detail: str


class FraudAnalysisRead(BaseModel):
    claim_id: str
    risk_score: int  # 0–100, weighted total of triggered signals
    risk_level: str  # LOW / MEDIUM / HIGH / CRITICAL
    recommendation: FraudRecommendation
    summary: str
    signals: list[FraudSignal]
    triggered_rules: list[str]
    # Retained detail fields for back-compat and quick reference.
    duplicate_claim_count: int
    repeated_incident_count: int
    suspicious_repair_cost: bool
    high_risk_garage: bool
    garage_name: str | None = None
    repair_estimate_amount: float | None = None

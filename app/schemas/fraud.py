from pydantic import BaseModel
from pydantic import Field


class FraudCheckRequest(BaseModel):
    garage_name: str | None = Field(default=None, min_length=2, max_length=120)
    repair_estimate_amount: float | None = Field(default=None, gt=0)


class FraudAnalysisRead(BaseModel):
    claim_id: str
    risk_level: str
    risk_score: int
    triggered_rules: list[str]
    duplicate_claim_count: int
    repeated_incident_count: int
    suspicious_repair_cost: bool
    high_risk_garage: bool
    garage_name: str | None = None
    repair_estimate_amount: float | None = None

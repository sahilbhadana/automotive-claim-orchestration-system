from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field

from app.models.settlement import PaymentMethod
from app.models.settlement import SettlementStatus


class InitiatePayoutRequest(BaseModel):
    payout_amount: float = Field(gt=0)
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    beneficiary_name: str = Field(min_length=2, max_length=200)
    beneficiary_account: str = Field(min_length=5, max_length=100)
    bank_ifsc: str | None = Field(default=None, max_length=20)


class SettlementRead(BaseModel):
    id: UUID
    claim_id: UUID
    payout_amount: float
    approved_amount: float | None
    payment_method: PaymentMethod
    beneficiary_name: str
    beneficiary_account: str
    bank_ifsc: str | None
    status: SettlementStatus
    retry_count: int
    max_retries: int
    failure_reason: str | None
    transaction_reference: str | None
    initiated_at: datetime
    completed_at: datetime | None
    next_retry_at: datetime | None

    model_config = {"from_attributes": True}


class SettlementStatusUpdate(BaseModel):
    status: SettlementStatus
    transaction_reference: str | None = None
    failure_reason: str | None = None

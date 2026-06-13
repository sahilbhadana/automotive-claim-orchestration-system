from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

from app.models.settlement import PaymentMethod
from app.models.settlement import SettlementBasis
from app.models.settlement import SettlementMode
from app.models.settlement import SettlementStatus


class InitiatePayoutRequest(BaseModel):
    """Either supply payout_amount directly, or supply assessed_amount
    with deductions and let the payable figure be computed as
    assessed - depreciation - excess."""

    payout_amount: float | None = Field(default=None, gt=0)
    assessed_amount: float | None = Field(default=None, gt=0)
    depreciation_amount: float = Field(default=0, ge=0)
    excess_amount: float = Field(default=0, ge=0)
    settlement_mode: SettlementMode = SettlementMode.REPAIR
    settlement_basis: SettlementBasis = SettlementBasis.REIMBURSEMENT
    garage_name: str | None = Field(default=None, min_length=2, max_length=200)
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER
    beneficiary_name: str = Field(min_length=2, max_length=200)
    beneficiary_account: str = Field(min_length=5, max_length=100)
    bank_ifsc: str | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def validate_payout_inputs(self) -> "InitiatePayoutRequest":
        if self.payout_amount is None and self.assessed_amount is None:
            raise ValueError("Either payout_amount or assessed_amount must be provided")
        if self.assessed_amount is not None:
            deductions = self.depreciation_amount + self.excess_amount
            if deductions >= self.assessed_amount:
                raise ValueError(
                    "Depreciation and excess deductions cannot equal or "
                    "exceed the assessed amount"
                )
        if self.settlement_basis == SettlementBasis.CASHLESS and not self.garage_name:
            raise ValueError(
                "Cashless settlements are paid directly to a network "
                "garage; garage_name is required"
            )
        return self

    def resolve_payout_amount(self) -> float:
        if self.assessed_amount is not None:
            return self.assessed_amount - self.depreciation_amount - self.excess_amount
        assert self.payout_amount is not None
        return self.payout_amount


class SettlementRead(BaseModel):
    id: UUID
    claim_id: UUID
    payout_amount: float
    approved_amount: float | None
    assessed_amount: float | None
    depreciation_amount: float
    excess_amount: float
    settlement_mode: SettlementMode
    settlement_basis: SettlementBasis
    garage_name: str | None
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

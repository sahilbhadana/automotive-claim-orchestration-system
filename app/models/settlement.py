from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.session import Base


class SettlementStatus(StrEnum):
    INITIATED = "INITIATED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"


class PaymentMethod(StrEnum):
    BANK_TRANSFER = "BANK_TRANSFER"
    CHEQUE = "CHEQUE"
    UPI = "UPI"
    NEFT = "NEFT"
    RTGS = "RTGS"


class SettlementMode(StrEnum):
    REPAIR = "REPAIR"
    CASH_LOSS = "CASH_LOSS"
    NET_OF_SALVAGE = "NET_OF_SALVAGE"
    TOTAL_LOSS = "TOTAL_LOSS"


class SettlementBasis(StrEnum):
    CASHLESS = "CASHLESS"
    REIMBURSEMENT = "REIMBURSEMENT"


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id"),
        nullable=False,
        index=True,
    )
    payout_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    approved_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method"),
        default=PaymentMethod.BANK_TRANSFER,
    )
    beneficiary_name: Mapped[str] = mapped_column(String(200))
    beneficiary_account: Mapped[str] = mapped_column(String(100))
    bank_ifsc: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[SettlementStatus] = mapped_column(
        Enum(SettlementStatus, name="settlement_status"),
        default=SettlementStatus.INITIATED,
        index=True,
    )
    settlement_mode: Mapped[SettlementMode] = mapped_column(
        Enum(SettlementMode, name="settlement_mode", native_enum=False, length=20),
        default=SettlementMode.REPAIR,
    )
    settlement_basis: Mapped[SettlementBasis] = mapped_column(
        Enum(SettlementBasis, name="settlement_basis", native_enum=False, length=20),
        default=SettlementBasis.REIMBURSEMENT,
    )
    # Cashless settlements are paid directly to a network garage.
    garage_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Payout breakdown: assessed loss minus depreciation minus excess.
    assessed_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    depreciation_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    excess_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    transaction_reference: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

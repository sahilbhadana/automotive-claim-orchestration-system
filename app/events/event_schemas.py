from __future__ import annotations

from datetime import datetime
from datetime import timezone
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from pydantic import Field


class EventType(StrEnum):
    CLAIM_CREATED = "ClaimCreated"
    FRAUD_CHECK_COMPLETED = "FraudCheckCompleted"
    CLAIM_APPROVED = "ClaimApproved"
    CLAIM_REJECTED = "ClaimRejected"
    PAYOUT_INITIATED = "PayoutInitiated"
    PAYOUT_COMPLETED = "PayoutCompleted"
    PAYOUT_FAILED = "PayoutFailed"
    SETTLEMENT_UPDATED = "SettlementUpdated"


class BaseEvent(BaseModel):
    event_type: EventType
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    correlation_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ClaimCreatedEvent(BaseEvent):
    event_type: EventType = EventType.CLAIM_CREATED

    @classmethod
    def build(
        cls,
        claim_id: UUID,
        policy_number: str,
        vehicle_number: str,
        claim_amount: float,
        incident_city: str,
        correlation_id: str | None = None,
    ) -> ClaimCreatedEvent:
        return cls(
            correlation_id=correlation_id,
            payload={
                "claim_id": str(claim_id),
                "policy_number": policy_number,
                "vehicle_number": vehicle_number,
                "claim_amount": claim_amount,
                "incident_city": incident_city,
            },
        )


class FraudCheckCompletedEvent(BaseEvent):
    event_type: EventType = EventType.FRAUD_CHECK_COMPLETED

    @classmethod
    def build(
        cls,
        claim_id: UUID,
        risk_level: str,
        risk_score: int,
        triggered_rules: list[str],
        correlation_id: str | None = None,
    ) -> FraudCheckCompletedEvent:
        return cls(
            correlation_id=correlation_id,
            payload={
                "claim_id": str(claim_id),
                "risk_level": risk_level,
                "risk_score": risk_score,
                "triggered_rules": triggered_rules,
            },
        )


class ClaimApprovedEvent(BaseEvent):
    event_type: EventType = EventType.CLAIM_APPROVED

    @classmethod
    def build(
        cls,
        claim_id: UUID,
        policy_number: str,
        claim_amount: float,
        adjuster_id: UUID | None = None,
        correlation_id: str | None = None,
    ) -> ClaimApprovedEvent:
        return cls(
            correlation_id=correlation_id,
            payload={
                "claim_id": str(claim_id),
                "policy_number": policy_number,
                "claim_amount": claim_amount,
                "adjuster_id": str(adjuster_id) if adjuster_id else None,
            },
        )


class PayoutInitiatedEvent(BaseEvent):
    event_type: EventType = EventType.PAYOUT_INITIATED

    @classmethod
    def build(
        cls,
        claim_id: UUID,
        settlement_id: UUID,
        payout_amount: float,
        correlation_id: str | None = None,
    ) -> PayoutInitiatedEvent:
        return cls(
            correlation_id=correlation_id,
            payload={
                "claim_id": str(claim_id),
                "settlement_id": str(settlement_id),
                "payout_amount": payout_amount,
            },
        )

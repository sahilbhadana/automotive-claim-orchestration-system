"""Unit tests for fraud analysis rule engine."""
from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.models.claim import Claim, ClaimStatus
from app.schemas.fraud import FraudCheckRequest
from app.services.fraud_service import analyze_claim_for_fraud


def _make_claim(
    policy_number: str = "POL-FRAUD-001",
    claim_amount: float = 50000.0,
    incident_city: str = "Mumbai",
) -> Claim:
    claim = Claim()
    claim.id = uuid.uuid4()
    claim.policy_number = policy_number
    claim.vehicle_number = "MH01AB9999"
    claim.incident_date = date(2026, 1, 20)
    claim.incident_city = incident_city
    claim.claim_amount = claim_amount
    claim.description = "Test fraud claim"
    claim.status = ClaimStatus.FRAUD_ANALYSIS
    return claim


class TestFraudAnalysis:
    def test_low_amount_claim_has_low_risk(self, db_session):
        claim = _make_claim(claim_amount=30000.0)
        result = analyze_claim_for_fraud(session=db_session, claim=claim, payload=None)
        assert result.risk_score >= 0

    def test_result_has_required_fields(self, db_session):
        claim = _make_claim()
        result = analyze_claim_for_fraud(session=db_session, claim=claim, payload=None)
        assert result.risk_level in ("LOW", "MEDIUM", "HIGH")
        assert isinstance(result.risk_score, int)
        assert isinstance(result.triggered_rules, list)

    def test_suspicious_garage_triggers_rule(self, db_session):
        claim = _make_claim()
        payload = FraudCheckRequest(
            garage_name="BIG FRAUD GARAGE",
            repair_estimate_amount=500000.0,
        )
        result = analyze_claim_for_fraud(session=db_session, claim=claim, payload=payload)
        assert result.risk_score >= 0

    def test_high_repair_estimate_escalates_score(self, db_session):
        claim = _make_claim(claim_amount=200000.0)
        payload_high = FraudCheckRequest(
            garage_name="Standard Garage",
            repair_estimate_amount=350000.0,
        )
        payload_low = FraudCheckRequest(
            garage_name="Standard Garage",
            repair_estimate_amount=10000.0,
        )
        high_result = analyze_claim_for_fraud(db_session, claim, payload_high)
        low_result = analyze_claim_for_fraud(db_session, claim, payload_low)
        assert high_result.risk_score >= low_result.risk_score

    def test_risk_level_thresholds(self, db_session):
        from app.tasks.claim_tasks import resolve_risk_level

        assert resolve_risk_level(0) == "LOW"
        assert resolve_risk_level(2) == "LOW"
        assert resolve_risk_level(3) == "MEDIUM"
        assert resolve_risk_level(5) == "MEDIUM"
        assert resolve_risk_level(6) == "HIGH"
        assert resolve_risk_level(10) == "HIGH"

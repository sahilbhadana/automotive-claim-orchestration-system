"""Unit tests for the fraud recommendation engine."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from app.models.claim import Claim, ClaimStatus, ClaimType
from app.schemas.fraud import FraudCheckRequest, FraudRecommendation
from app.services.fraud_service import (
    WEIGHTS,
    analyze_claim_for_fraud,
    get_latest_assessment,
    persist_fraud_assessment,
)


def _make_claim(
    session=None,
    *,
    policy_number: str = "POL-FRAUD-001",
    vehicle: str = "MH01AB9999",
    incident_date: date = date(2026, 1, 20),
    claim_amount: float = 50000.0,
    claim_type: ClaimType = ClaimType.ACCIDENT,
    idv: float | None = None,
    license_expiry_date: date | None = date(2030, 1, 1),
    persist: bool = False,
) -> Claim:
    claim = Claim(
        id=uuid.uuid4(),
        policy_number=policy_number,
        vehicle_number=vehicle,
        incident_date=incident_date,
        incident_city="Mumbai",
        claim_amount=claim_amount,
        description="Test fraud claim",
        status=ClaimStatus.FRAUD_ANALYSIS,
        claim_type=claim_type,
        idv=idv,
        license_expiry_date=license_expiry_date,
        created_at=datetime(2026, 1, 21, tzinfo=timezone.utc),
    )
    if session is not None and persist:
        session.add(claim)
        session.flush()
    return claim


class TestFraudRecommendationEngine:
    def test_clean_claim_is_cleared(self, db_session):
        claim = _make_claim(db_session)
        result = analyze_claim_for_fraud(db_session, claim)
        assert result.recommendation == FraudRecommendation.CLEAR
        assert result.risk_level == "LOW"
        assert "duplicate_claim" not in result.triggered_rules

    def test_duplicate_claim_recommends_investigate(self, db_session):
        first = _make_claim(db_session, persist=True)
        second = _make_claim(
            db_session,
            persist=True,
            policy_number=first.policy_number,
            vehicle=first.vehicle_number,
            incident_date=first.incident_date,
        )
        result = analyze_claim_for_fraud(db_session, second)
        assert "duplicate_claim" in result.triggered_rules
        assert result.recommendation == FraudRecommendation.INVESTIGATE
        assert result.risk_score >= WEIGHTS["duplicate_claim"]

    def test_high_risk_garage_is_flagged(self, db_session):
        claim = _make_claim(db_session)
        result = analyze_claim_for_fraud(
            db_session, claim, FraudCheckRequest(garage_name="Rapid Cash Garage")
        )
        assert "high_risk_garage" in result.triggered_rules
        assert result.recommendation in (
            FraudRecommendation.REVIEW,
            FraudRecommendation.INVESTIGATE,
        )

    def test_expired_licence_is_a_signal(self, db_session):
        claim = _make_claim(db_session, license_expiry_date=date(2026, 1, 1))
        result = analyze_claim_for_fraud(db_session, claim)
        assert "invalid_licence" in result.triggered_rules

    def test_claim_near_idv_is_a_signal(self, db_session):
        claim = _make_claim(db_session, claim_amount=95000.0, idv=100000.0)
        result = analyze_claim_for_fraud(db_session, claim)
        assert "claim_near_idv" in result.triggered_rules

    def test_inflated_estimate_is_a_signal(self, db_session):
        claim = _make_claim(db_session, claim_amount=200000.0)
        result = analyze_claim_for_fraud(
            db_session, claim, FraudCheckRequest(repair_estimate_amount=350000.0)
        )
        assert "inflated_estimate" in result.triggered_rules

    def test_signal_matrix_is_complete(self, db_session):
        claim = _make_claim(db_session)
        result = analyze_claim_for_fraud(db_session, claim)
        assert len(result.signals) == len(WEIGHTS)
        assert all(s.weight > 0 for s in result.signals)
        # score equals the sum of triggered signal weights (capped at 100)
        expected = min(sum(s.weight for s in result.signals if s.triggered), 100)
        assert result.risk_score == expected

    def test_score_is_capped_at_100(self, db_session):
        # Stack duplicate + garage + expired licence + inflated estimate.
        first = _make_claim(db_session, persist=True)
        claim = _make_claim(
            db_session,
            persist=True,
            policy_number=first.policy_number,
            vehicle=first.vehicle_number,
            incident_date=first.incident_date,
            claim_amount=200000.0,
            idv=200000.0,
            license_expiry_date=date(2026, 1, 1),
        )
        result = analyze_claim_for_fraud(
            db_session,
            claim,
            FraudCheckRequest(
                garage_name="Metro Collision Hub", repair_estimate_amount=400000.0
            ),
        )
        assert result.risk_score == 100
        assert result.recommendation == FraudRecommendation.INVESTIGATE


class TestFraudAssessmentPersistence:
    def test_persist_and_fetch_latest(self, db_session):
        claim = _make_claim(db_session, persist=True)
        result = analyze_claim_for_fraud(db_session, claim)
        persist_fraud_assessment(db_session, claim, result)

        latest = get_latest_assessment(db_session, claim.id)
        assert latest is not None
        assert latest.recommendation == result.recommendation.value
        assert latest.risk_score == result.risk_score
        # the full payload round-trips through the JSON column
        assert latest.result["claim_id"] == str(claim.id)

    def test_latest_returns_most_recent(self, db_session):
        claim = _make_claim(db_session, persist=True)
        first = analyze_claim_for_fraud(db_session, claim)
        persist_fraud_assessment(db_session, claim, first)
        second = analyze_claim_for_fraud(
            db_session, claim, FraudCheckRequest(garage_name="Rapid Cash Garage")
        )
        persist_fraud_assessment(db_session, claim, second)

        latest = get_latest_assessment(db_session, claim.id)
        assert latest.result["recommendation"] == second.recommendation.value

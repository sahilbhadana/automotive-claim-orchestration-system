"""Unit tests for the realistic claim lifecycle: type-specific
workflows, FIR rules, surveyor TAT, procedural guards, and the payout
breakdown."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from app.models.claim import Claim, ClaimStatus, ClaimType
from app.models.settlement import SettlementBasis, SettlementMode
from app.models.survey import InspectionMode, Survey, SurveyRecommendation  # noqa: F401
from app.schemas.claim import ClaimCreate
from app.schemas.settlement import InitiatePayoutRequest
from app.services.settlement_service import PayoutError, initiate_payout
from app.services.survey_service import (
    SurveyError,
    appoint_surveyor,
    is_report_overdue,
    record_inspection,
    submit_survey_report,
)
from app.services.workflow_service import (
    WorkflowTransitionError,
    execute_workflow_step,
    get_allowed_transitions,
)


def _claim_payload(**overrides) -> dict:
    base = {
        "policy_number": "POL-LIFE-001",
        "vehicle_number": "GJ01AA0001",
        "incident_date": "2026-05-01",
        "incident_city": "Ahmedabad",
        "claim_amount": 80000.0,
        "description": "Lifecycle test claim with enough detail",
    }
    base.update(overrides)
    return base


def _make_claim(
    status: ClaimStatus = ClaimStatus.CLAIM_CREATED,
    claim_type: ClaimType = ClaimType.ACCIDENT,
    idv: float | None = None,
) -> Claim:
    claim = Claim()
    claim.id = uuid.uuid4()
    claim.policy_number = "POL-LIFE-001"
    claim.vehicle_number = "GJ01AA0001"
    claim.incident_date = date(2026, 5, 1)
    claim.incident_city = "Ahmedabad"
    claim.claim_amount = 80000.0
    claim.description = "Lifecycle test claim"
    claim.status = status
    claim.claim_type = claim_type
    claim.idv = idv
    return claim


class TestFirValidationRules:
    def test_theft_claim_requires_fir(self):
        with pytest.raises(ValidationError, match="FIR"):
            ClaimCreate(**_claim_payload(claim_type="THEFT", idv=400000))

    def test_third_party_claim_requires_fir(self):
        with pytest.raises(ValidationError, match="FIR"):
            ClaimCreate(**_claim_payload(claim_type="THIRD_PARTY"))

    def test_theft_claim_requires_idv(self):
        with pytest.raises(ValidationError, match="IDV"):
            ClaimCreate(**_claim_payload(claim_type="THEFT", fir_number="FIR-123"))

    def test_accident_claim_needs_no_fir(self):
        claim = ClaimCreate(**_claim_payload())
        assert claim.claim_type == ClaimType.ACCIDENT
        assert claim.fir_number is None

    def test_valid_theft_claim(self):
        claim = ClaimCreate(
            **_claim_payload(claim_type="THEFT", fir_number="FIR-2026-001", idv=400000)
        )
        assert claim.claim_type == ClaimType.THEFT


class TestTypeSpecificWorkflows:
    def test_theft_path_skips_inspection_and_repair(self):
        transitions = get_allowed_transitions(
            ClaimStatus.ADJUSTER_ASSIGNMENT, ClaimType.THEFT
        )
        assert transitions == [ClaimStatus.SURVEY_REPORT_REVIEW]

    def test_own_damage_path_requires_inspection(self):
        transitions = get_allowed_transitions(
            ClaimStatus.ADJUSTER_ASSIGNMENT, ClaimType.ACCIDENT
        )
        assert transitions == [ClaimStatus.VEHICLE_INSPECTION]

    def test_third_party_path_goes_to_legal_review(self):
        transitions = get_allowed_transitions(
            ClaimStatus.POLICY_VALIDATION, ClaimType.THIRD_PARTY
        )
        assert ClaimStatus.LEGAL_REVIEW in transitions
        assert ClaimStatus.FRAUD_ANALYSIS not in transitions

    def test_natural_disaster_follows_own_damage_path(self):
        assert get_allowed_transitions(
            ClaimStatus.VEHICLE_INSPECTION, ClaimType.NATURAL_DISASTER
        ) == get_allowed_transitions(ClaimStatus.VEHICLE_INSPECTION, ClaimType.ACCIDENT)


class TestProceduralGuards:
    def test_document_verification_requires_uploaded_document(self, db_session):
        claim = _make_claim(ClaimStatus.DOCUMENT_VERIFICATION)
        db_session.add(claim)
        db_session.flush()

        with pytest.raises(WorkflowTransitionError, match="document"):
            execute_workflow_step(db_session, claim, ClaimStatus.POLICY_VALIDATION)

    def test_vehicle_inspection_requires_appointed_surveyor(self, db_session):
        claim = _make_claim(ClaimStatus.ADJUSTER_ASSIGNMENT)
        db_session.add(claim)
        db_session.flush()

        with pytest.raises(WorkflowTransitionError, match="surveyor"):
            execute_workflow_step(db_session, claim, ClaimStatus.VEHICLE_INSPECTION)

    def test_repair_estimation_requires_completed_inspection(self, db_session):
        claim = _make_claim(ClaimStatus.VEHICLE_INSPECTION)
        db_session.add(claim)
        db_session.flush()
        appoint_surveyor(db_session, claim, "R. Mehta")

        with pytest.raises(WorkflowTransitionError, match="inspected"):
            execute_workflow_step(db_session, claim, ClaimStatus.REPAIR_ESTIMATION)

    def test_survey_report_review_requires_submitted_report(self, db_session):
        claim = _make_claim(ClaimStatus.REPAIR_ESTIMATION)
        db_session.add(claim)
        db_session.flush()
        survey = appoint_surveyor(db_session, claim, "R. Mehta")
        record_inspection(db_session, survey, InspectionMode.PHYSICAL)

        with pytest.raises(WorkflowTransitionError, match="report"):
            execute_workflow_step(db_session, claim, ClaimStatus.SURVEY_REPORT_REVIEW)


class TestSurveyLifecycle:
    def test_appointment_sets_15_day_report_deadline(self, db_session):
        claim = _make_claim()
        db_session.add(claim)
        db_session.flush()

        survey = appoint_surveyor(db_session, claim, "R. Mehta")
        assert survey.report_due_at is not None
        delta = survey.report_due_at - survey.appointed_at
        assert delta.days == 15
        assert is_report_overdue(survey) is False

    def test_duplicate_appointment_rejected(self, db_session):
        claim = _make_claim()
        db_session.add(claim)
        db_session.flush()
        appoint_surveyor(db_session, claim, "R. Mehta")

        with pytest.raises(SurveyError, match="already appointed"):
            appoint_surveyor(db_session, claim, "S. Iyer")

    def test_report_requires_prior_inspection(self, db_session):
        claim = _make_claim()
        db_session.add(claim)
        db_session.flush()
        survey = appoint_surveyor(db_session, claim, "R. Mehta")

        with pytest.raises(SurveyError, match="inspection"):
            submit_survey_report(
                db_session,
                survey,
                estimated_loss_amount=60000,
                recommended_amount=52000,
                recommendation=SurveyRecommendation.APPROVE,
            )

    def test_recommended_cannot_exceed_estimated(self, db_session):
        claim = _make_claim()
        db_session.add(claim)
        db_session.flush()
        survey = appoint_surveyor(db_session, claim, "R. Mehta")
        record_inspection(db_session, survey, InspectionMode.DIGITAL, "video survey")

        with pytest.raises(SurveyError, match="exceed"):
            submit_survey_report(
                db_session,
                survey,
                estimated_loss_amount=50000,
                recommended_amount=60000,
                recommendation=SurveyRecommendation.APPROVE,
            )

    def test_full_survey_lifecycle(self, db_session):
        claim = _make_claim()
        db_session.add(claim)
        db_session.flush()
        survey = appoint_surveyor(db_session, claim, "R. Mehta")
        survey = record_inspection(db_session, survey, InspectionMode.PHYSICAL)
        survey = submit_survey_report(
            db_session,
            survey,
            estimated_loss_amount=60000,
            recommended_amount=52000,
            recommendation=SurveyRecommendation.APPROVE,
            notes="Front panel replacement, depreciation applies",
        )
        assert survey.report_submitted_at is not None
        assert float(survey.recommended_amount) == 52000


class TestPayoutBreakdown:
    def _request(self, **overrides) -> InitiatePayoutRequest:
        base = {
            "assessed_amount": 60000.0,
            "depreciation_amount": 6000.0,
            "excess_amount": 1000.0,
            "beneficiary_name": "Test User",
            "beneficiary_account": "1234567890",
        }
        base.update(overrides)
        return InitiatePayoutRequest(**base)

    def test_payout_computed_from_breakdown(self, db_session):
        claim = _make_claim(ClaimStatus.APPROVED)
        db_session.add(claim)
        db_session.flush()

        settlement = initiate_payout(db_session, claim, self._request())
        assert float(settlement.payout_amount) == 53000.0
        assert float(settlement.depreciation_amount) == 6000.0
        assert float(settlement.excess_amount) == 1000.0

    def test_deductions_cannot_consume_assessed_amount(self):
        with pytest.raises(ValidationError, match="deductions"):
            self._request(depreciation_amount=50000, excess_amount=10000)

    def test_cashless_requires_garage(self):
        with pytest.raises(ValidationError, match="garage"):
            self._request(settlement_basis="CASHLESS")

    def test_cashless_with_garage_accepted(self, db_session):
        claim = _make_claim(ClaimStatus.APPROVED)
        db_session.add(claim)
        db_session.flush()

        settlement = initiate_payout(
            db_session,
            claim,
            self._request(settlement_basis="CASHLESS", garage_name="Apex Motors Pune"),
        )
        assert settlement.settlement_basis == SettlementBasis.CASHLESS
        assert settlement.garage_name == "Apex Motors Pune"

    def test_payout_capped_at_idv(self, db_session):
        claim = _make_claim(ClaimStatus.APPROVED, idv=40000)
        db_session.add(claim)
        db_session.flush()

        with pytest.raises(PayoutError, match="Insured Declared Value"):
            initiate_payout(db_session, claim, self._request())

    def test_theft_claim_settles_as_total_loss(self, db_session):
        claim = _make_claim(
            ClaimStatus.APPROVED, claim_type=ClaimType.THEFT, idv=400000
        )
        db_session.add(claim)
        db_session.flush()

        settlement = initiate_payout(
            db_session,
            claim,
            self._request(
                assessed_amount=400000, depreciation_amount=0, excess_amount=1000
            ),
        )
        assert settlement.settlement_mode == SettlementMode.TOTAL_LOSS
        assert float(settlement.payout_amount) == 399000.0

    def test_either_payout_or_assessed_required(self):
        with pytest.raises(ValidationError, match="payout_amount or assessed_amount"):
            InitiatePayoutRequest(
                beneficiary_name="Test User",
                beneficiary_account="1234567890",
            )

"""Unit tests for the realistic claim lifecycle: type-specific
workflows, FIR rules, surveyor TAT, procedural guards, and the payout
breakdown."""

from __future__ import annotations

import uuid
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.models.claim import Claim, ClaimStatus, ClaimType
from app.models.policy import CoverageType, Policy, PolicyStatus
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
    survey_is_mandatory,
)


def _claim_payload(**overrides) -> dict:
    base = {
        "policy_number": "POL-LIFE-001",
        "vehicle_number": "GJ01AA0001",
        "incident_date": "2026-05-01",
        "incident_city": "Ahmedabad",
        "claim_amount": 80000.0,
        "description": "Lifecycle test claim with enough detail",
        "driving_license_number": "GJ0120100012345",
        "license_expiry_date": "2030-01-01",
    }
    base.update(overrides)
    return base


def _make_claim(
    status: ClaimStatus = ClaimStatus.CLAIM_CREATED,
    claim_type: ClaimType = ClaimType.ACCIDENT,
    idv: float | None = None,
    claim_amount: float = 80000.0,
    license_expiry_date: date | None = date(2030, 1, 1),
) -> Claim:
    claim = Claim()
    claim.id = uuid.uuid4()
    claim.policy_number = "POL-LIFE-001"
    claim.vehicle_number = "GJ01AA0001"
    claim.incident_date = date(2026, 5, 1)
    claim.incident_city = "Ahmedabad"
    claim.claim_amount = claim_amount
    claim.description = "Lifecycle test claim"
    claim.status = status
    claim.claim_type = claim_type
    claim.idv = idv
    claim.driving_license_number = "GJ0120100012345"
    claim.license_expiry_date = license_expiry_date
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


class TestLicenceRequirement:
    def test_accident_claim_requires_licence(self):
        with pytest.raises(ValidationError, match="licence"):
            ClaimCreate(
                **{
                    **_claim_payload(),
                    "driving_license_number": None,
                    "license_expiry_date": None,
                }
            )

    def test_third_party_claim_requires_licence(self):
        payload = _claim_payload(claim_type="THIRD_PARTY", fir_number="FIR-1", idv=None)
        payload["driving_license_number"] = None
        payload["license_expiry_date"] = None
        with pytest.raises(ValidationError, match="licence"):
            ClaimCreate(**payload)

    def test_theft_claim_needs_no_licence(self):
        claim = ClaimCreate(
            **{
                **_claim_payload(claim_type="THEFT", fir_number="FIR-9", idv=400000),
                "driving_license_number": None,
                "license_expiry_date": None,
            }
        )
        assert claim.claim_type == ClaimType.THEFT


def _seed_policy(session, **overrides) -> Policy:
    base = {
        "policy_number": "POL-LIFE-001",
        "insured_name": "Test Insured",
        "vehicle_number": "GJ01AA0001",
        "coverage_type": CoverageType.COMPREHENSIVE,
        "status": PolicyStatus.ACTIVE,
        "effective_date": date(2026, 1, 1),
        "expiry_date": date(2027, 1, 1),
        "is_vehicle_insured": True,
    }
    base.update(overrides)
    policy = Policy(**base)
    session.add(policy)
    session.flush()
    return policy


class TestPolicyValidationGate:
    def _claim_at_validation(self, session, **kwargs) -> Claim:
        claim = _make_claim(ClaimStatus.POLICY_VALIDATION, **kwargs)
        session.add(claim)
        session.flush()
        return claim

    def test_expired_licence_blocks_progression(self, db_session):
        claim = self._claim_at_validation(
            db_session, license_expiry_date=date(2026, 4, 1)
        )  # expired before the 2026-05-01 incident
        with pytest.raises(WorkflowTransitionError, match="licence had expired"):
            execute_workflow_step(db_session, claim, ClaimStatus.FRAUD_ANALYSIS)

    def test_valid_claim_with_no_policy_on_file_proceeds(self, db_session):
        claim = self._claim_at_validation(db_session)
        _, updated = execute_workflow_step(
            db_session, claim, ClaimStatus.FRAUD_ANALYSIS
        )
        assert updated.status == ClaimStatus.FRAUD_ANALYSIS

    def test_lapsed_policy_blocks_progression(self, db_session):
        _seed_policy(db_session, status=PolicyStatus.LAPSED)
        claim = self._claim_at_validation(db_session)
        with pytest.raises(WorkflowTransitionError, match="not active"):
            execute_workflow_step(db_session, claim, ClaimStatus.FRAUD_ANALYSIS)

    def test_coverage_mismatch_blocks_own_damage(self, db_session):
        # A third-party-only policy cannot cover an own-damage accident claim.
        _seed_policy(db_session, coverage_type=CoverageType.THIRD_PARTY)
        claim = self._claim_at_validation(db_session)
        with pytest.raises(WorkflowTransitionError, match="does not cover"):
            execute_workflow_step(db_session, claim, ClaimStatus.FRAUD_ANALYSIS)

    def test_active_matching_policy_proceeds(self, db_session):
        _seed_policy(db_session)
        claim = self._claim_at_validation(db_session)
        _, updated = execute_workflow_step(
            db_session, claim, ClaimStatus.FRAUD_ANALYSIS
        )
        assert updated.status == ClaimStatus.FRAUD_ANALYSIS


class TestMandatorySurveyThreshold:
    def test_small_own_damage_claim_skips_survey(self):
        assert survey_is_mandatory(ClaimType.ACCIDENT, 40000) is False
        transitions = get_allowed_transitions(
            ClaimStatus.ADJUSTER_ASSIGNMENT, ClaimType.ACCIDENT, 40000
        )
        assert ClaimStatus.FINAL_APPROVAL in transitions

    def test_large_own_damage_claim_requires_survey(self):
        assert survey_is_mandatory(ClaimType.ACCIDENT, 80000) is True
        transitions = get_allowed_transitions(
            ClaimStatus.ADJUSTER_ASSIGNMENT, ClaimType.ACCIDENT, 80000
        )
        assert transitions == [ClaimStatus.VEHICLE_INSPECTION]

    def test_threshold_boundary_is_mandatory(self):
        # Exactly ₹50,000 is at/above the threshold, so survey is mandatory.
        assert survey_is_mandatory(ClaimType.ACCIDENT, 50000) is True


class TestTotalLossDetection:
    def _inspected_survey(self, db_session, idv):
        claim = _make_claim(idv=idv)
        db_session.add(claim)
        db_session.flush()
        survey = appoint_surveyor(db_session, claim, "R. Mehta")
        record_inspection(db_session, survey, InspectionMode.PHYSICAL)
        return claim, survey

    def test_total_loss_flagged_above_threshold(self, db_session):
        # Estimate 320000 is >= 75% of IDV 400000 (=300000).
        _, survey = self._inspected_survey(db_session, idv=400000)
        survey = submit_survey_report(
            db_session,
            survey,
            estimated_loss_amount=320000,
            recommended_amount=300000,
            recommendation=SurveyRecommendation.APPROVE,
        )
        assert survey.total_loss_flagged is True

    def test_repairable_loss_not_flagged(self, db_session):
        # Estimate 120000 is below 75% of IDV 400000.
        _, survey = self._inspected_survey(db_session, idv=400000)
        survey = submit_survey_report(
            db_session,
            survey,
            estimated_loss_amount=120000,
            recommended_amount=110000,
            recommendation=SurveyRecommendation.APPROVE,
        )
        assert survey.total_loss_flagged is False


class TestIntimationDelay:
    def test_delay_computed_and_flagged(self):
        from app.schemas.claim import ClaimRead

        claim = _make_claim()
        claim.id = uuid.uuid4()
        claim.adjuster_id = None
        claim.claimant_id = None
        claim.created_at = datetime(2026, 5, 10, 9, 0, 0)  # 9 days after incident
        claim.updated_at = datetime(2026, 5, 10, 9, 0, 0)
        read = ClaimRead.model_validate(claim)
        assert read.intimation_delay_days == 9
        assert read.delayed_intimation is True

    def test_prompt_intimation_not_flagged(self):
        from app.schemas.claim import ClaimRead

        claim = _make_claim()
        claim.id = uuid.uuid4()
        claim.adjuster_id = None
        claim.claimant_id = None
        claim.created_at = datetime(2026, 5, 1, 18, 0, 0)  # same day
        claim.updated_at = datetime(2026, 5, 1, 18, 0, 0)
        read = ClaimRead.model_validate(claim)
        assert read.intimation_delay_days == 0
        assert read.delayed_intimation is False

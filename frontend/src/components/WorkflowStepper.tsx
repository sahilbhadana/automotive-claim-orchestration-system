import { Check } from "lucide-react";
import type { ClaimStatus, ClaimType } from "../api/types";

// Each claim type follows its own pipeline, mirroring the backend
// state machines.
const PIPELINES: Record<ClaimType, ClaimStatus[]> = {
  ACCIDENT: [
    "CLAIM_CREATED",
    "DOCUMENT_VERIFICATION",
    "POLICY_VALIDATION",
    "FRAUD_ANALYSIS",
    "ADJUSTER_ASSIGNMENT",
    "VEHICLE_INSPECTION",
    "REPAIR_ESTIMATION",
    "SURVEY_REPORT_REVIEW",
    "FINAL_APPROVAL",
    "APPROVED",
    "PAYOUT",
  ],
  NATURAL_DISASTER: [
    "CLAIM_CREATED",
    "DOCUMENT_VERIFICATION",
    "POLICY_VALIDATION",
    "FRAUD_ANALYSIS",
    "ADJUSTER_ASSIGNMENT",
    "VEHICLE_INSPECTION",
    "REPAIR_ESTIMATION",
    "SURVEY_REPORT_REVIEW",
    "FINAL_APPROVAL",
    "APPROVED",
    "PAYOUT",
  ],
  THEFT: [
    "CLAIM_CREATED",
    "DOCUMENT_VERIFICATION",
    "POLICY_VALIDATION",
    "FRAUD_ANALYSIS",
    "ADJUSTER_ASSIGNMENT",
    "SURVEY_REPORT_REVIEW",
    "FINAL_APPROVAL",
    "APPROVED",
    "PAYOUT",
  ],
  THIRD_PARTY: [
    "CLAIM_CREATED",
    "DOCUMENT_VERIFICATION",
    "POLICY_VALIDATION",
    "LEGAL_REVIEW",
    "FINAL_APPROVAL",
    "APPROVED",
    "PAYOUT",
  ],
};

const LABELS: Record<string, string> = {
  CLAIM_CREATED: "Registered",
  DOCUMENT_VERIFICATION: "Documents",
  POLICY_VALIDATION: "Policy",
  FRAUD_ANALYSIS: "Fraud Check",
  ADJUSTER_ASSIGNMENT: "Surveyor",
  VEHICLE_INSPECTION: "Inspection",
  REPAIR_ESTIMATION: "Repair Est.",
  SURVEY_REPORT_REVIEW: "Survey Report",
  LEGAL_REVIEW: "Legal / MACT",
  FINAL_APPROVAL: "Final Review",
  APPROVED: "Approved",
  PAYOUT: "Settled",
};

export function WorkflowStepper({
  status,
  claimType = "ACCIDENT",
}: {
  status: ClaimStatus;
  claimType?: ClaimType;
}) {
  if (status === "REJECTED") {
    return (
      <div className="stepper stepper-rejected">
        <span className="badge badge-red">CLAIM REJECTED</span>
      </div>
    );
  }

  const pipeline = PIPELINES[claimType] ?? PIPELINES.ACCIDENT;
  const currentIndex = pipeline.indexOf(status);

  return (
    <div className="stepper">
      {pipeline.map((step, i) => {
        const state =
          i < currentIndex ? "done" : i === currentIndex ? "active" : "todo";
        return (
          <div key={step} className={`step step-${state}`}>
            <div className="step-dot">
              {state === "done" ? <Check size={13} /> : i + 1}
            </div>
            <div className="step-label">{LABELS[step]}</div>
            {i < pipeline.length - 1 && <div className="step-line" />}
          </div>
        );
      })}
    </div>
  );
}

import type { ClaimStatus } from "../api/types";

const PIPELINE: ClaimStatus[] = [
  "CLAIM_CREATED",
  "DOCUMENT_VERIFICATION",
  "POLICY_VALIDATION",
  "FRAUD_ANALYSIS",
  "ADJUSTER_ASSIGNMENT",
  "REPAIR_ESTIMATION",
  "FINAL_APPROVAL",
  "APPROVED",
  "PAYOUT",
];

const LABELS: Record<string, string> = {
  CLAIM_CREATED: "Created",
  DOCUMENT_VERIFICATION: "Documents",
  POLICY_VALIDATION: "Policy",
  FRAUD_ANALYSIS: "Fraud Check",
  ADJUSTER_ASSIGNMENT: "Adjuster",
  REPAIR_ESTIMATION: "Repair Est.",
  FINAL_APPROVAL: "Final Review",
  APPROVED: "Approved",
  PAYOUT: "Payout",
};

export function WorkflowStepper({ status }: { status: ClaimStatus }) {
  if (status === "REJECTED") {
    return (
      <div className="stepper stepper-rejected">
        <span className="badge badge-red">CLAIM REJECTED</span>
      </div>
    );
  }

  const currentIndex = PIPELINE.indexOf(status);

  return (
    <div className="stepper">
      {PIPELINE.map((step, i) => {
        const state =
          i < currentIndex ? "done" : i === currentIndex ? "active" : "todo";
        return (
          <div key={step} className={`step step-${state}`}>
            <div className="step-dot">{state === "done" ? "✓" : i + 1}</div>
            <div className="step-label">{LABELS[step]}</div>
            {i < PIPELINE.length - 1 && <div className="step-line" />}
          </div>
        );
      })}
    </div>
  );
}

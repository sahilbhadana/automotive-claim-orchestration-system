import type { ClaimStatus, FailedTaskStatus, SettlementStatus } from "../api/types";

type AnyStatus = ClaimStatus | SettlementStatus | FailedTaskStatus | string;

const STATUS_COLORS: Record<string, string> = {
  // Claim statuses
  CLAIM_CREATED: "badge-blue",
  DOCUMENT_VERIFICATION: "badge-amber",
  POLICY_VALIDATION: "badge-amber",
  FRAUD_ANALYSIS: "badge-purple",
  ADJUSTER_ASSIGNMENT: "badge-blue",
  VEHICLE_INSPECTION: "badge-blue",
  REPAIR_ESTIMATION: "badge-amber",
  SURVEY_REPORT_REVIEW: "badge-purple",
  LEGAL_REVIEW: "badge-purple",
  FINAL_APPROVAL: "badge-purple",
  // Survey statuses
  APPOINTED: "badge-blue",
  INSPECTION_DONE: "badge-amber",
  REPORT_SUBMITTED: "badge-green",
  APPROVED: "badge-green",
  REJECTED: "badge-red",
  PAYOUT: "badge-green",
  // Settlement statuses
  INITIATED: "badge-blue",
  PROCESSING: "badge-amber",
  COMPLETED: "badge-green",
  FAILED: "badge-red",
  REVERSED: "badge-purple",
  // Failed-task statuses
  PENDING: "badge-amber",
  RETRYING: "badge-blue",
  DEAD: "badge-red",
  RECOVERED: "badge-green",
};

export function StatusBadge({ status }: { status: AnyStatus }) {
  const cls = STATUS_COLORS[status] ?? "badge-gray";
  return <span className={`badge ${cls}`}>{status.replace(/_/g, " ")}</span>;
}

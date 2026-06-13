// Mirrors the Pydantic schemas exposed by the FastAPI backend.

export type UserRole = "customer" | "adjuster" | "supervisor" | "admin";

export type ClaimStatus =
  | "CLAIM_CREATED"
  | "DOCUMENT_VERIFICATION"
  | "POLICY_VALIDATION"
  | "FRAUD_ANALYSIS"
  | "ADJUSTER_ASSIGNMENT"
  | "VEHICLE_INSPECTION"
  | "REPAIR_ESTIMATION"
  | "SURVEY_REPORT_REVIEW"
  | "LEGAL_REVIEW"
  | "FINAL_APPROVAL"
  | "APPROVED"
  | "REJECTED"
  | "PAYOUT";

export type ClaimType = "ACCIDENT" | "THEFT" | "THIRD_PARTY" | "NATURAL_DISASTER";

export type SettlementMode = "REPAIR" | "CASH_LOSS" | "NET_OF_SALVAGE" | "TOTAL_LOSS";

export type SettlementBasis = "CASHLESS" | "REIMBURSEMENT";

export type SurveyStatus = "APPOINTED" | "INSPECTION_DONE" | "REPORT_SUBMITTED";

export type InspectionMode = "PHYSICAL" | "DIGITAL";

export type SurveyRecommendation = "APPROVE" | "REJECT";

export type SettlementStatus =
  | "INITIATED"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED"
  | "REVERSED";

export type PaymentMethod = "BANK_TRANSFER" | "CHEQUE" | "UPI" | "NEFT" | "RTGS";

export type FailedTaskStatus = "PENDING" | "RETRYING" | "DEAD" | "RECOVERED";

export type DocumentType = "ACCIDENT_PHOTO" | "FIR" | "RC";

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenRead {
  access_token: string;
  token_type: string;
}

export interface Claim {
  id: string;
  policy_number: string;
  vehicle_number: string;
  incident_date: string;
  incident_city: string;
  claim_amount: number;
  description: string;
  claim_type: ClaimType;
  fir_number: string | null;
  idv: number | null;
  driving_license_number: string | null;
  license_expiry_date: string | null;
  adjuster_id: string | null;
  claimant_id: string | null;
  status: ClaimStatus;
  created_at: string;
  updated_at: string;
  intimation_delay_days: number;
  delayed_intimation: boolean;
}

export interface ClaimCreate {
  policy_number: string;
  vehicle_number: string;
  incident_date: string;
  incident_city: string;
  claim_amount: number;
  description: string;
  claim_type: ClaimType;
  fir_number?: string | null;
  idv?: number | null;
  driving_license_number?: string | null;
  license_expiry_date?: string | null;
}

export interface Survey {
  id: string;
  claim_id: string;
  surveyor_name: string;
  status: SurveyStatus;
  inspection_mode: InspectionMode | null;
  inspection_notes: string | null;
  estimated_loss_amount: number | null;
  recommended_amount: number | null;
  recommendation: SurveyRecommendation | null;
  report_notes: string | null;
  total_loss_flagged: boolean;
  appointed_at: string;
  inspected_at: string | null;
  report_submitted_at: string | null;
  report_due_at: string | null;
  report_overdue: boolean;
}

export interface WorkflowState {
  claim_id: string;
  current_status: ClaimStatus;
  allowed_transitions: ClaimStatus[];
  terminal: boolean;
}

export interface WorkflowExecution {
  claim_id: string;
  previous_status: ClaimStatus;
  current_status: ClaimStatus;
  executed_transition: string;
  allowed_next_transitions: ClaimStatus[];
  terminal: boolean;
  reason: string | null;
}

export interface ClaimDocument {
  id: string;
  claim_id: string;
  document_type: DocumentType;
  original_filename: string;
  storage_path: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
}

export interface FraudAnalysis {
  claim_id: string;
  risk_level: string;
  risk_score: number;
  triggered_rules: string[];
  duplicate_claim_count: number;
  repeated_incident_count: number;
  suspicious_repair_cost: boolean;
  high_risk_garage: boolean;
  garage_name: string | null;
  repair_estimate_amount: number | null;
}

export interface Settlement {
  id: string;
  claim_id: string;
  payout_amount: number;
  approved_amount: number | null;
  assessed_amount: number | null;
  depreciation_amount: number;
  excess_amount: number;
  settlement_mode: SettlementMode;
  settlement_basis: SettlementBasis;
  garage_name: string | null;
  payment_method: PaymentMethod;
  beneficiary_name: string;
  beneficiary_account: string;
  bank_ifsc: string | null;
  status: SettlementStatus;
  retry_count: number;
  max_retries: number;
  failure_reason: string | null;
  transaction_reference: string | null;
  initiated_at: string;
  completed_at: string | null;
  next_retry_at: string | null;
}

export interface InitiatePayoutRequest {
  payout_amount?: number | null;
  assessed_amount?: number | null;
  depreciation_amount?: number;
  excess_amount?: number;
  settlement_mode?: SettlementMode;
  settlement_basis?: SettlementBasis;
  garage_name?: string | null;
  payment_method: PaymentMethod;
  beneficiary_name: string;
  beneficiary_account: string;
  bank_ifsc?: string | null;
}

export interface FailedTask {
  id: string;
  task_name: string;
  error_message: string;
  error_type: string;
  retry_count: number;
  max_retries: number;
  status: FailedTaskStatus;
  next_retry_at: string | null;
  failed_at: string;
  recovered_at: string | null;
}

export interface RetryQueueStats {
  total: number;
  pending: number;
  retrying: number;
  dead: number;
  recovered: number;
}

export interface AuditLogEntry {
  id: string;
  claim_id: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  actor: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface Adjuster {
  id: string;
  full_name: string;
  city: string;
  expertise: string;
  max_active_claims: number;
  is_active: boolean;
}

export interface AdjusterAssignment {
  claim_id: string;
  adjuster_id: string;
  adjuster_name: string;
  city_match: boolean;
  workload_count: number;
  max_active_claims: number;
  required_expertise: string;
  assigned_expertise: string;
}

export interface MetricsSummary {
  metrics: Record<string, number>;
  note?: string;
}

export interface HealthStatus {
  status: string;
  service?: string;
  environment?: string;
  database?: string;
}

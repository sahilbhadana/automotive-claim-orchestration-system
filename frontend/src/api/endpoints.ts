import { api, getToken, ApiError } from "./client";
import type {
  Adjuster,
  AdjusterAssignment,
  AuditLogEntry,
  Claim,
  ClaimCreate,
  ClaimDocument,
  ClaimStatus,
  FailedTask,
  FraudAnalysis,
  HealthStatus,
  InitiatePayoutRequest,
  MetricsSummary,
  RetryQueueStats,
  Settlement,
  Survey,
  TokenRead,
  User,
  WorkflowExecution,
  WorkflowState,
} from "./types";

// --- Auth ---
export const login = (username: string, password: string) =>
  api.post<TokenRead>("/auth/login", { username, password });

export const register = (payload: {
  username: string;
  email: string;
  full_name: string;
  password: string;
}) => api.post<User>("/auth/register", payload);

export const fetchProfile = () => api.get<User>("/auth/me");

// --- Claims ---
export const listClaims = () => api.get<Claim[]>("/claims");
export const getClaim = (id: string) => api.get<Claim>(`/claims/${id}`);
export const createClaim = (payload: ClaimCreate) =>
  api.post<Claim>("/claims", payload);

// --- Workflow ---
export const getWorkflowState = (claimId: string) =>
  api.get<WorkflowState>(`/claims/${claimId}/workflow`);

export const executeWorkflowStep = (
  claimId: string,
  targetStatus: ClaimStatus,
  reason?: string,
) =>
  api.post<WorkflowExecution>(`/claims/${claimId}/workflow/execute`, {
    target_status: targetStatus,
    reason: reason ?? null,
  });

// --- Documents ---
export const listDocuments = (claimId: string) =>
  api.get<ClaimDocument[]>(`/claims/${claimId}/documents`);

export const uploadDocument = (
  claimId: string,
  documentType: string,
  file: File,
) => {
  const form = new FormData();
  form.append("document_type", documentType);
  form.append("file", file);
  return api.post<ClaimDocument>(`/claims/${claimId}/documents`, form);
};

// Fetches the file with the auth header, then triggers a browser save.
export const downloadDocument = async (
  claimId: string,
  documentId: string,
  filename: string,
): Promise<void> => {
  const token = getToken();
  const response = await fetch(
    `/api/v1/claims/${claimId}/documents/${documentId}/download`,
    { headers: token ? { Authorization: `Bearer ${token}` } : {} },
  );
  if (!response.ok) {
    let detail = `Download failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // non-JSON error body; keep generic message
    }
    throw new ApiError(response.status, detail);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
};

// --- Fraud ---
export const analyzeFraud = (
  claimId: string,
  garageName?: string,
  repairEstimate?: number,
) =>
  api.post<FraudAnalysis>(`/claims/${claimId}/fraud/analyze`, {
    garage_name: garageName || null,
    repair_estimate_amount: repairEstimate || null,
  });

export const getFraudAssessment = (claimId: string) =>
  api.get<FraudAnalysis>(`/claims/${claimId}/fraud`);

// --- Adjusters ---
export const listAdjusters = () => api.get<Adjuster[]>("/adjusters");
export const assignAdjuster = (claimId: string) =>
  api.post<AdjusterAssignment>(`/claims/${claimId}/adjuster/assign`);

// --- Settlements ---
export const listClaimSettlements = (claimId: string) =>
  api.get<Settlement[]>(`/claims/${claimId}/settlements`);

export const initiatePayout = (claimId: string, payload: InitiatePayoutRequest) =>
  api.post<Settlement>(`/claims/${claimId}/settlements`, payload);

export const getSettlement = (settlementId: string) =>
  api.get<Settlement>(`/settlements/${settlementId}`);

export const retrySettlement = (settlementId: string) =>
  api.post<Settlement>(`/settlements/${settlementId}/retry`);

export const reverseSettlement = (settlementId: string, reason: string) =>
  api.post<Settlement>(
    `/settlements/${settlementId}/reverse?reason=${encodeURIComponent(reason)}`,
  );

// --- Survey ---
export const getSurvey = (claimId: string) =>
  api.get<Survey>(`/claims/${claimId}/survey`);

export const appointSurveyor = (claimId: string, surveyorName: string) =>
  api.post<Survey>(`/claims/${claimId}/survey/appoint`, {
    surveyor_name: surveyorName,
  });

export const recordInspection = (
  claimId: string,
  inspectionMode: string,
  notes?: string,
) =>
  api.post<Survey>(`/claims/${claimId}/survey/inspection`, {
    inspection_mode: inspectionMode,
    notes: notes || null,
  });

export const submitSurveyReport = (
  claimId: string,
  payload: {
    estimated_loss_amount: number;
    recommended_amount: number;
    recommendation: string;
    notes?: string | null;
  },
) => api.post<Survey>(`/claims/${claimId}/survey/report`, payload);

// --- Audit ---
export const listClaimActivity = (claimId: string) =>
  api.get<AuditLogEntry[]>(`/claims/${claimId}/activity`);

// --- Dead-Letter Queue ---
export const listDlq = () => api.get<FailedTask[]>("/dlq");
export const listAllFailedTasks = (status?: string) =>
  api.get<FailedTask[]>(status ? `/dlq/all?status=${status}` : "/dlq/all");
export const getDlqStats = () => api.get<RetryQueueStats>("/dlq/stats");
export const requeueTask = (taskId: string) =>
  api.post<FailedTask>(`/dlq/${taskId}/retry`);
export const scheduleTaskRetry = (taskId: string) =>
  api.post<FailedTask>(`/dlq/${taskId}/schedule-retry`);
export const dismissTask = (taskId: string) =>
  api.delete<{ deleted: boolean }>(`/dlq/${taskId}`);

// --- Observability ---
export const getMetricsSummary = () => api.get<MetricsSummary>("/metrics/summary");
export const getHealth = () => api.get<HealthStatus>("/health");
export const getReadiness = () => api.get<HealthStatus>("/ready");

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Check, Circle, Download } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import {
  analyzeFraud,
  assignAdjuster,
  downloadDocument,
  executeWorkflowStep,
  getClaim,
  getWorkflowState,
  initiatePayout,
  listClaimActivity,
  listClaimSettlements,
  listDocuments,
  uploadDocument,
} from "../api/endpoints";
import type {
  AuditLogEntry,
  Claim,
  ClaimDocument,
  ClaimStatus,
  DocumentType,
  FraudAnalysis,
  PaymentMethod,
  Settlement,
  WorkflowState,
} from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { StatusBadge } from "../components/StatusBadge";
import { useToast } from "../components/Toast";
import { WorkflowStepper } from "../components/WorkflowStepper";

const formatINR = (amount: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);

const DOC_LABELS: Record<DocumentType, string> = {
  ACCIDENT_PHOTO: "Accident Photo",
  FIR: "FIR Report",
  RC: "Registration Certificate",
};

type Tab = "workflow" | "documents" | "fraud" | "settlements" | "activity";

export function ClaimDetailPage() {
  const { claimId } = useParams<{ claimId: string }>();
  const { user } = useAuth();
  const [claim, setClaim] = useState<Claim | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowState | null>(null);
  const [documents, setDocuments] = useState<ClaimDocument[]>([]);
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [activity, setActivity] = useState<AuditLogEntry[]>([]);
  const [fraud, setFraud] = useState<FraudAnalysis | null>(null);
  const [tab, setTab] = useState<Tab>("workflow");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  const canManage =
    user?.role === "adjuster" || user?.role === "supervisor" || user?.role === "admin";
  const canPayout = user?.role === "supervisor" || user?.role === "admin";

  const refresh = useCallback(async () => {
    if (!claimId) return;
    try {
      const [claimData, workflowData, docs, activityData] = await Promise.all([
        getClaim(claimId),
        getWorkflowState(claimId),
        listDocuments(claimId),
        listClaimActivity(claimId),
      ]);
      setClaim(claimData);
      setWorkflow(workflowData);
      setDocuments(docs);
      setActivity(activityData);
      if (canManage) {
        // Settlement listing is restricted to adjuster/supervisor/admin roles.
        const stl = await listClaimSettlements(claimId).catch(() => []);
        setSettlements(stl);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load claim");
    } finally {
      setLoading(false);
    }
  }, [claimId, canManage]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (loading) return <div className="page-loading">Loading claim…</div>;
  if (!claim || !claimId) {
    return (
      <div className="page">
        <div className="empty-state">
          <h2>Claim not found</h2>
          <p>{error}</p>
          <Link to="/claims" className="btn btn-primary">
            Back to claims
          </Link>
        </div>
      </div>
    );
  }

  const flash = (msg: string) => toast.success(msg);
  const fail = (err: unknown) =>
    toast.error(err instanceof Error ? err.message : "Operation failed");

  const handleTransition = async (target: ClaimStatus) => {
    try {
      const result = await executeWorkflowStep(claimId, target);
      flash(`Workflow advanced: ${result.executed_transition}`);
      await refresh();
    } catch (err) {
      fail(err);
    }
  };

  const handleAssignAdjuster = async () => {
    try {
      const result = await assignAdjuster(claimId);
      flash(
        `Assigned ${result.adjuster_name} (${result.assigned_expertise}, workload ${result.workload_count}/${result.max_active_claims})`,
      );
      await refresh();
    } catch (err) {
      fail(err);
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="breadcrumb">
            <Link to="/claims">Claims</Link> / <span className="mono">{claim.id.slice(0, 8)}</span>
          </div>
          <h1>
            {claim.vehicle_number}{" "}
            <StatusBadge status={claim.status} />
          </h1>
          <p className="page-subtitle">
            Policy {claim.policy_number} · {claim.incident_city} ·{" "}
            {claim.incident_date} · {formatINR(claim.claim_amount)}
          </p>
        </div>
      </div>

      <div className="card">
        <WorkflowStepper status={claim.status} />
      </div>

      <div className="tabs">
        {(
          [
            ["workflow", "Workflow"],
            ["documents", `Documents (${documents.length})`],
            ["fraud", "Fraud Analysis"],
            ...(canManage
              ? [["settlements", `Settlements (${settlements.length})`] as [Tab, string]]
              : []),
            ["activity", `Activity (${activity.length})`],
          ] as [Tab, string][]
        ).map(([key, label]) => (
          <button
            key={key}
            className={`tab${tab === key ? " tab-active" : ""}`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "workflow" && (
        <WorkflowTab
          claim={claim}
          workflow={workflow}
          canManage={canManage}
          onTransition={handleTransition}
          onAssignAdjuster={handleAssignAdjuster}
        />
      )}
      {tab === "documents" && (
        <DocumentsTab
          claimId={claimId}
          documents={documents}
          onUploaded={refresh}
          onError={fail}
          onNotice={flash}
        />
      )}
      {tab === "fraud" && (
        <FraudTab
          claimId={claimId}
          fraud={fraud}
          canManage={canManage}
          onResult={setFraud}
          onError={fail}
        />
      )}
      {tab === "settlements" && canManage && (
        <SettlementsTab
          claimId={claimId}
          claim={claim}
          settlements={settlements}
          canPayout={canPayout}
          onChanged={refresh}
          onError={fail}
          onNotice={flash}
        />
      )}
      {tab === "activity" && <ActivityTab activity={activity} />}
    </div>
  );
}

function WorkflowTab({
  claim,
  workflow,
  canManage,
  onTransition,
  onAssignAdjuster,
}: {
  claim: Claim;
  workflow: WorkflowState | null;
  canManage: boolean;
  onTransition: (target: ClaimStatus) => void;
  onAssignAdjuster: () => void;
}) {
  return (
    <div className="card">
      <h3>Claim details</h3>
      <div className="detail-grid">
        <div>
          <span className="detail-label">Claim ID</span>
          <span className="mono">{claim.id}</span>
        </div>
        <div>
          <span className="detail-label">Adjuster</span>
          <span>{claim.adjuster_id ? <code>{claim.adjuster_id.slice(0, 8)}</code> : "Not assigned"}</span>
        </div>
        <div>
          <span className="detail-label">Filed</span>
          <span>{new Date(claim.created_at).toLocaleString()}</span>
        </div>
        <div>
          <span className="detail-label">Last updated</span>
          <span>{new Date(claim.updated_at).toLocaleString()}</span>
        </div>
      </div>
      <p className="claim-description">{claim.description}</p>

      {canManage && workflow && (
        <>
          <h3>Workflow actions</h3>
          {workflow.terminal ? (
            <p className="muted">
              This claim is in a terminal state — no further transitions are allowed.
            </p>
          ) : (
            <div className="action-row">
              {workflow.allowed_transitions.map((target) => (
                <button
                  key={target}
                  className={`btn ${
                    target === "REJECTED" ? "btn-danger" : "btn-primary"
                  }`}
                  onClick={() => onTransition(target)}
                >
                  {target === "REJECTED"
                    ? "Reject Claim"
                    : `Advance to ${target.replace(/_/g, " ")}`}
                </button>
              ))}
              {claim.status === "ADJUSTER_ASSIGNMENT" && (
                <button className="btn btn-secondary" onClick={onAssignAdjuster}>
                  Auto-assign Best Adjuster
                </button>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function DocumentsTab({
  claimId,
  documents,
  onUploaded,
  onError,
  onNotice,
}: {
  claimId: string;
  documents: ClaimDocument[];
  onUploaded: () => void;
  onError: (err: unknown) => void;
  onNotice: (msg: string) => void;
}) {
  const { user } = useAuth();
  const [docType, setDocType] = useState<DocumentType>("ACCIDENT_PHOTO");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  const canUpload = user?.role === "customer";
  const uploadedTypes = new Set(documents.map((d) => d.document_type));
  const requiredTypes: DocumentType[] = ["ACCIDENT_PHOTO", "FIR", "RC"];

  const handleUpload = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    try {
      await uploadDocument(claimId, docType, file);
      onNotice(`Uploaded ${file.name}`);
      setFile(null);
      onUploaded();
    } catch (err) {
      onError(err);
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = async (doc: ClaimDocument) => {
    setDownloadingId(doc.id);
    try {
      await downloadDocument(claimId, doc.id, doc.original_filename);
    } catch (err) {
      onError(err);
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div className="card">
      <h3>Required documents</h3>
      <div className="doc-checklist">
        {requiredTypes.map((t) => (
          <div
            key={t}
            className={`doc-check-item${uploadedTypes.has(t) ? " is-done" : ""}`}
          >
            {uploadedTypes.has(t) ? <Check size={13} /> : <Circle size={11} />}
            {DOC_LABELS[t]}
          </div>
        ))}
      </div>

      {canUpload ? (
        <form onSubmit={handleUpload} className="upload-form">
          <select
            value={docType}
            onChange={(e) => setDocType(e.target.value as DocumentType)}
          >
            {requiredTypes.map((t) => (
              <option key={t} value={t}>
                {DOC_LABELS[t]}
              </option>
            ))}
          </select>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <button className="btn btn-primary" disabled={!file || busy}>
            {busy ? "Uploading…" : "Upload"}
          </button>
        </form>
      ) : (
        <p className="muted small">
          Documents are uploaded by the claimant. As claims staff you can
          review and download them below.
        </p>
      )}

      {documents.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Filename</th>
                <th>Size</th>
                <th>Uploaded</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>{DOC_LABELS[doc.document_type] ?? doc.document_type}</td>
                  <td className="mono">{doc.original_filename}</td>
                  <td>{(doc.size_bytes / 1024).toFixed(1)} KB</td>
                  <td>{new Date(doc.created_at).toLocaleString()}</td>
                  <td>
                    <button
                      className="btn btn-ghost btn-small"
                      onClick={() => handleDownload(doc)}
                      disabled={downloadingId === doc.id}
                    >
                      <Download size={13} />
                      {downloadingId === doc.id ? "Saving…" : "Download"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function FraudTab({
  claimId,
  fraud,
  canManage,
  onResult,
  onError,
}: {
  claimId: string;
  fraud: FraudAnalysis | null;
  canManage: boolean;
  onResult: (result: FraudAnalysis) => void;
  onError: (err: unknown) => void;
}) {
  const [garage, setGarage] = useState("");
  const [estimate, setEstimate] = useState("");
  const [busy, setBusy] = useState(false);

  const handleAnalyze = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const result = await analyzeFraud(
        claimId,
        garage || undefined,
        estimate ? Number(estimate) : undefined,
      );
      onResult(result);
    } catch (err) {
      onError(err);
    } finally {
      setBusy(false);
    }
  };

  const riskClass =
    fraud?.risk_level === "HIGH"
      ? "risk-high"
      : fraud?.risk_level === "MEDIUM"
        ? "risk-medium"
        : "risk-low";

  return (
    <div className="card">
      <h3>Fraud analysis</h3>
      {canManage ? (
        <form onSubmit={handleAnalyze} className="form-row form-row-end">
          <label className="field">
            <span>Garage name (optional)</span>
            <input
              value={garage}
              onChange={(e) => setGarage(e.target.value)}
              placeholder="Tech Auto Repair"
            />
          </label>
          <label className="field">
            <span>Repair estimate (optional)</span>
            <input
              type="number"
              value={estimate}
              onChange={(e) => setEstimate(e.target.value)}
              min={1}
              placeholder="32000"
            />
          </label>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? "Analyzing…" : "Run Analysis"}
          </button>
        </form>
      ) : (
        <p className="muted">Fraud analysis is run by claims staff.</p>
      )}

      {fraud && (
        <div className="fraud-result">
          <div className={`risk-banner ${riskClass}`}>
            <div className="risk-score">{fraud.risk_score}</div>
            <div>
              <div className="risk-level">{fraud.risk_level} RISK</div>
              <div className="muted">
                {fraud.triggered_rules.length} rule
                {fraud.triggered_rules.length === 1 ? "" : "s"} triggered
              </div>
            </div>
          </div>
          {fraud.triggered_rules.length > 0 && (
            <ul className="rule-list">
              {fraud.triggered_rules.map((rule) => (
                <li key={rule}>⚠ {rule.replace(/_/g, " ")}</li>
              ))}
            </ul>
          )}
          <div className="detail-grid">
            <div>
              <span className="detail-label">Duplicate claims</span>
              <span>{fraud.duplicate_claim_count}</span>
            </div>
            <div>
              <span className="detail-label">Repeated incidents</span>
              <span>{fraud.repeated_incident_count}</span>
            </div>
            <div>
              <span className="detail-label">Suspicious repair cost</span>
              <span>{fraud.suspicious_repair_cost ? "Yes" : "No"}</span>
            </div>
            <div>
              <span className="detail-label">High-risk garage</span>
              <span>{fraud.high_risk_garage ? "Yes" : "No"}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SettlementsTab({
  claimId,
  claim,
  settlements,
  canPayout,
  onChanged,
  onError,
  onNotice,
}: {
  claimId: string;
  claim: Claim;
  settlements: Settlement[];
  canPayout: boolean;
  onChanged: () => void;
  onError: (err: unknown) => void;
  onNotice: (msg: string) => void;
}) {
  const [form, setForm] = useState({
    payout_amount: String(claim.claim_amount),
    payment_method: "BANK_TRANSFER" as PaymentMethod,
    beneficiary_name: "",
    beneficiary_account: "",
    bank_ifsc: "",
  });
  const [busy, setBusy] = useState(false);

  const hasActive = settlements.some(
    (s) => s.status !== "FAILED" && s.status !== "REVERSED",
  );

  const handleInitiate = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await initiatePayout(claimId, {
        payout_amount: Number(form.payout_amount),
        payment_method: form.payment_method,
        beneficiary_name: form.beneficiary_name,
        beneficiary_account: form.beneficiary_account,
        bank_ifsc: form.bank_ifsc || null,
      });
      onNotice("Payout initiated — processing in background");
      onChanged();
    } catch (err) {
      onError(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card">
      <h3>Settlements</h3>

      {settlements.length === 0 ? (
        <p className="muted">No settlements yet for this claim.</p>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Amount</th>
                <th>Method</th>
                <th>Beneficiary</th>
                <th>Status</th>
                <th>Retries</th>
                <th>Reference</th>
                <th>Initiated</th>
              </tr>
            </thead>
            <tbody>
              {settlements.map((s) => (
                <tr key={s.id}>
                  <td className="amount">{formatINR(s.payout_amount)}</td>
                  <td>{s.payment_method.replace(/_/g, " ")}</td>
                  <td>{s.beneficiary_name}</td>
                  <td>
                    <StatusBadge status={s.status} />
                  </td>
                  <td>
                    {s.retry_count}/{s.max_retries}
                  </td>
                  <td className="mono">{s.transaction_reference ?? "—"}</td>
                  <td>{new Date(s.initiated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {canPayout && claim.status === "APPROVED" && !hasActive && (
        <>
          <h3>Initiate payout</h3>
          <form onSubmit={handleInitiate}>
            <div className="form-row">
              <label className="field">
                <span>Payout amount (₹)</span>
                <input
                  type="number"
                  value={form.payout_amount}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, payout_amount: e.target.value }))
                  }
                  required
                  min={1}
                />
              </label>
              <label className="field">
                <span>Payment method</span>
                <select
                  value={form.payment_method}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      payment_method: e.target.value as PaymentMethod,
                    }))
                  }
                >
                  <option value="BANK_TRANSFER">Bank transfer</option>
                  <option value="NEFT">NEFT</option>
                  <option value="RTGS">RTGS</option>
                  <option value="UPI">UPI</option>
                  <option value="CHEQUE">Cheque</option>
                </select>
              </label>
            </div>
            <div className="form-row">
              <label className="field">
                <span>Beneficiary name</span>
                <input
                  value={form.beneficiary_name}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, beneficiary_name: e.target.value }))
                  }
                  required
                  minLength={2}
                />
              </label>
              <label className="field">
                <span>Account number</span>
                <input
                  value={form.beneficiary_account}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      beneficiary_account: e.target.value,
                    }))
                  }
                  required
                  minLength={5}
                />
              </label>
              <label className="field">
                <span>IFSC (optional)</span>
                <input
                  value={form.bank_ifsc}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, bank_ifsc: e.target.value }))
                  }
                />
              </label>
            </div>
            <button className="btn btn-primary" disabled={busy}>
              {busy ? "Initiating…" : "Initiate Payout"}
            </button>
          </form>
        </>
      )}

      {canPayout && claim.status !== "APPROVED" && settlements.length === 0 && (
        <p className="muted">
          Payouts can only be initiated once the claim reaches APPROVED status.
        </p>
      )}
    </div>
  );
}

function ActivityTab({ activity }: { activity: AuditLogEntry[] }) {
  if (activity.length === 0) {
    return (
      <div className="card">
        <p className="muted">No activity recorded yet.</p>
      </div>
    );
  }
  return (
    <div className="card">
      <h3>Activity timeline</h3>
      <div className="timeline">
        {activity.map((event) => (
          <div key={event.id} className="timeline-item">
            <div className="timeline-dot" />
            <div className="timeline-body">
              <div className="timeline-action">
                {event.action.replace(/_/g, " ")}
              </div>
              <div className="muted">
                {event.actor} · {new Date(event.created_at).toLocaleString()}
              </div>
              {Object.keys(event.details).length > 0 && (
                <pre className="timeline-details">
                  {JSON.stringify(event.details, null, 2)}
                </pre>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

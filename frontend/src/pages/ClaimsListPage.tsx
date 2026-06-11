import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listClaims } from "../api/endpoints";
import type { Claim, ClaimStatus } from "../api/types";
import { StatusBadge } from "../components/StatusBadge";

const ALL_STATUSES: (ClaimStatus | "ALL")[] = [
  "ALL",
  "CLAIM_CREATED",
  "DOCUMENT_VERIFICATION",
  "POLICY_VALIDATION",
  "FRAUD_ANALYSIS",
  "ADJUSTER_ASSIGNMENT",
  "REPAIR_ESTIMATION",
  "FINAL_APPROVAL",
  "APPROVED",
  "REJECTED",
  "PAYOUT",
];

const formatINR = (amount: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);

export function ClaimsListPage() {
  const [claims, setClaims] = useState<Claim[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<ClaimStatus | "ALL">("ALL");
  const [search, setSearch] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    listClaims()
      .then(setClaims)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    return claims.filter((c) => {
      if (statusFilter !== "ALL" && c.status !== statusFilter) return false;
      if (search) {
        const q = search.toLowerCase();
        return (
          c.policy_number.toLowerCase().includes(q) ||
          c.vehicle_number.toLowerCase().includes(q) ||
          c.incident_city.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [claims, statusFilter, search]);

  const stats = useMemo(
    () => ({
      total: claims.length,
      active: claims.filter(
        (c) => c.status !== "REJECTED" && c.status !== "PAYOUT",
      ).length,
      approved: claims.filter(
        (c) => c.status === "APPROVED" || c.status === "PAYOUT",
      ).length,
      rejected: claims.filter((c) => c.status === "REJECTED").length,
    }),
    [claims],
  );

  if (loading) return <div className="page-loading">Loading claims…</div>;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Claims</h1>
          <p className="page-subtitle">Track and manage insurance claims</p>
        </div>
        <Link to="/claims/new" className="btn btn-primary">
          + File New Claim
        </Link>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.total}</div>
          <div className="stat-label">Total claims</div>
        </div>
        <div className="stat-card">
          <div className="stat-value stat-blue">{stats.active}</div>
          <div className="stat-label">In progress</div>
        </div>
        <div className="stat-card">
          <div className="stat-value stat-green">{stats.approved}</div>
          <div className="stat-label">Approved / Paid</div>
        </div>
        <div className="stat-card">
          <div className="stat-value stat-red">{stats.rejected}</div>
          <div className="stat-label">Rejected</div>
        </div>
      </div>

      <div className="toolbar">
        <input
          className="search-input"
          placeholder="Search policy, vehicle, or city…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as ClaimStatus | "ALL")}
        >
          {ALL_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s === "ALL" ? "All statuses" : s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state">
          <h2>No claims found</h2>
          <p>
            {claims.length === 0
              ? "File your first claim to get started."
              : "No claims match the current filters."}
          </p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Policy</th>
                <th>Vehicle</th>
                <th>Incident</th>
                <th>City</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Filed</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((claim) => (
                <tr
                  key={claim.id}
                  className="row-clickable"
                  onClick={() => navigate(`/claims/${claim.id}`)}
                >
                  <td className="mono">{claim.policy_number}</td>
                  <td className="mono">{claim.vehicle_number}</td>
                  <td>{claim.incident_date}</td>
                  <td>{claim.incident_city}</td>
                  <td className="amount">{formatINR(claim.claim_amount)}</td>
                  <td>
                    <StatusBadge status={claim.status} />
                  </td>
                  <td>{new Date(claim.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

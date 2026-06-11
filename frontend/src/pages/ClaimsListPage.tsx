import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Search } from "lucide-react";
import { listClaims } from "../api/endpoints";
import type { Claim, ClaimStatus } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { DonutChart } from "../components/DonutChart";
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
  const { user } = useAuth();
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
      exposure: claims
        .filter((c) => c.status !== "REJECTED")
        .reduce((sum, c) => sum + c.claim_amount, 0),
    }),
    [claims],
  );

  if (loading) {
    return (
      <div className="page">
        <div className="page-header">
          <div>
            <h1>Claims</h1>
            <p className="page-subtitle">Loading your workspace…</p>
          </div>
        </div>
        <div className="stat-grid">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton skeleton-stat" />
          ))}
        </div>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="skeleton skeleton-row" />
        ))}
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="eyebrow">Workspace</div>
          <h1>{user?.role === "customer" ? "My Claims" : "Claims"}</h1>
          <p className="page-subtitle">
            {user?.role === "customer"
              ? "Your claims, from first notice of loss to settled payout."
              : "Every claim in the book, from first notice of loss to settled payout."}
          </p>
        </div>
        <Link to="/claims/new" className="btn btn-primary">
          <Plus size={15} />
          File New Claim
        </Link>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="stat-strip">
        <div className="stat-cell">
          <div className="stat-label">Total claims</div>
          <div className="stat-value">{stats.total}</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">In review</div>
          <div className="stat-value">{stats.active}</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Approved &amp; paid</div>
          <div className="stat-value stat-green">{stats.approved}</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Rejected</div>
          <div className="stat-value stat-red">{stats.rejected}</div>
        </div>
      </div>

      {claims.length > 0 && (
        <div className="chart-row">
          <div className="card" style={{ marginBottom: 0 }}>
            <h3>Pipeline distribution</h3>
            <DonutChart
              centerLabel={String(stats.total)}
              centerSub="claims"
              segments={[
                {
                  label: "In review",
                  value: stats.active,
                  color: "var(--info)",
                },
                {
                  label: "Approved & paid",
                  value: stats.approved,
                  color: "var(--ok)",
                },
                {
                  label: "Rejected",
                  value: stats.rejected,
                  color: "var(--err)",
                },
              ]}
            />
          </div>
          <div className="card" style={{ marginBottom: 0 }}>
            <h3>Open exposure</h3>
            <div className="stat-value" style={{ fontSize: 40 }}>
              {formatINR(stats.exposure)}
            </div>
            <p className="muted" style={{ marginTop: 12, maxWidth: 420 }}>
              The amount you would pay if every open claim settled at full
              value today. Rejected claims are excluded.
            </p>
          </div>
        </div>
      )}

      <div className="toolbar">
        <div className="search-wrap">
          <Search size={15} />
          <input
            className="search-input"
            placeholder="Search policy, vehicle, or city…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) =>
            setStatusFilter(e.target.value as ClaimStatus | "ALL")
          }
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

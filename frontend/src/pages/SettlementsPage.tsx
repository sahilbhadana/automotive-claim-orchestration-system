import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  listClaimSettlements,
  listClaims,
  retrySettlement,
  reverseSettlement,
} from "../api/endpoints";
import type { Claim, Settlement } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { StatusBadge } from "../components/StatusBadge";

const formatINR = (amount: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);

interface SettlementRow extends Settlement {
  claim?: Claim;
}

export function SettlementsPage() {
  const { user } = useAuth();
  const [rows, setRows] = useState<SettlementRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const isAdmin = user?.role === "admin";

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const claims = await listClaims();
      const byId = new Map(claims.map((c) => [c.id, c]));
      // Settlements only exist for claims that reached APPROVED or beyond.
      const candidates = claims.filter((c) =>
        ["APPROVED", "PAYOUT"].includes(c.status),
      );
      const settled = await Promise.all(
        candidates.map((c) =>
          listClaimSettlements(c.id).catch(() => [] as Settlement[]),
        ),
      );
      const all: SettlementRow[] = settled
        .flat()
        .map((s) => ({ ...s, claim: byId.get(s.claim_id) }))
        .sort(
          (a, b) =>
            new Date(b.initiated_at).getTime() -
            new Date(a.initiated_at).getTime(),
        );
      setRows(all);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settlements");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRetry = async (id: string) => {
    try {
      await retrySettlement(id);
      setNotice("Retry queued — the payout will be reprocessed shortly.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retry failed");
    }
  };

  const handleReverse = async (id: string) => {
    const reason = window.prompt("Reason for reversing this settlement:");
    if (!reason) return;
    try {
      await reverseSettlement(id, reason);
      setNotice("Settlement reversed.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Reverse failed");
    }
  };

  const totals = {
    completed: rows.filter((r) => r.status === "COMPLETED"),
    inFlight: rows.filter((r) =>
      ["INITIATED", "PROCESSING"].includes(r.status),
    ),
    failed: rows.filter((r) => r.status === "FAILED"),
  };

  if (loading) return <div className="page-loading">Loading settlements…</div>;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Settlements</h1>
          <p className="page-subtitle">Payout tracking across all claims</p>
        </div>
        <button className="btn btn-ghost" onClick={load}>
          ↻ Refresh
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-value stat-green">
            {formatINR(
              totals.completed.reduce((sum, r) => sum + r.payout_amount, 0),
            )}
          </div>
          <div className="stat-label">
            Paid out ({totals.completed.length} settlements)
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-value stat-blue">{totals.inFlight.length}</div>
          <div className="stat-label">In flight</div>
        </div>
        <div className="stat-card">
          <div className="stat-value stat-red">{totals.failed.length}</div>
          <div className="stat-label">Failed</div>
        </div>
      </div>

      {rows.length === 0 ? (
        <div className="empty-state">
          <h2>No settlements</h2>
          <p>Payouts appear here once claims are approved and settled.</p>
        </div>
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Claim</th>
                <th>Amount</th>
                <th>Method</th>
                <th>Beneficiary</th>
                <th>Status</th>
                <th>Retries</th>
                <th>Initiated</th>
                {isAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.id}>
                  <td>
                    {s.claim ? (
                      <Link to={`/claims/${s.claim_id}`} className="mono">
                        {s.claim.vehicle_number}
                      </Link>
                    ) : (
                      <span className="mono">{s.claim_id.slice(0, 8)}</span>
                    )}
                  </td>
                  <td className="amount">{formatINR(s.payout_amount)}</td>
                  <td>{s.payment_method.replace(/_/g, " ")}</td>
                  <td>{s.beneficiary_name}</td>
                  <td>
                    <StatusBadge status={s.status} />
                    {s.failure_reason && (
                      <div className="muted small">{s.failure_reason}</div>
                    )}
                  </td>
                  <td>
                    {s.retry_count}/{s.max_retries}
                  </td>
                  <td>{new Date(s.initiated_at).toLocaleString()}</td>
                  {isAdmin && (
                    <td>
                      <div className="action-row-compact">
                        {s.status === "FAILED" && (
                          <button
                            className="btn btn-small"
                            onClick={() => handleRetry(s.id)}
                          >
                            Retry
                          </button>
                        )}
                        {s.status === "COMPLETED" && (
                          <button
                            className="btn btn-small btn-danger"
                            onClick={() => handleReverse(s.id)}
                          >
                            Reverse
                          </button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

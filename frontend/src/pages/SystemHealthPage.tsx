import { useCallback, useEffect, useState } from "react";
import { getHealth, getMetricsSummary, getReadiness } from "../api/endpoints";
import type { HealthStatus, MetricsSummary } from "../api/types";

// Business metrics worth surfacing on the dashboard, with friendly labels.
const FEATURED_METRICS: [string, string][] = [
  ["claims_created_total", "Claims created"],
  ["claims_status_transitions_total", "Workflow transitions"],
  ["fraud_checks_total", "Fraud checks run"],
  ["payouts_initiated_total", "Payouts initiated"],
  ["payouts_completed_total", "Payouts completed"],
  ["payouts_failed_total", "Payouts failed"],
  ["dlq_depth", "DLQ depth"],
  ["http_requests_total", "HTTP requests"],
];

export function SystemHealthPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [readiness, setReadiness] = useState<HealthStatus | null>(null);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showAll, setShowAll] = useState(false);

  const load = useCallback(async () => {
    try {
      const [h, r, m] = await Promise.all([
        getHealth(),
        getReadiness(),
        getMetricsSummary(),
      ]);
      setHealth(h);
      setReadiness(r);
      setMetrics(m);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load system status");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, [load]);

  if (loading) return <div className="page-loading">Loading system status…</div>;

  const metricEntries = Object.entries(metrics?.metrics ?? {});
  const findMetric = (name: string): number | null => {
    const exact = metrics?.metrics?.[name];
    if (exact !== undefined) return exact;
    // Counter samples are exported with a _total or base-name variant.
    const fuzzy = metricEntries.find(([k]) => k.startsWith(name));
    return fuzzy ? fuzzy[1] : null;
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>System Health</h1>
          <p className="page-subtitle">
            Live service status and Prometheus metrics · auto-refreshes every 15s
          </p>
        </div>
        <button className="btn btn-ghost" onClick={load}>
          ↻ Refresh
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="stat-grid">
        <div className="stat-card">
          <div
            className={`health-pill ${health?.status === "ok" ? "stat-green" : "stat-red"}`}
          >
            <span className="pulse" style={{ background: "currentColor" }} />
            {health?.status === "ok" ? "Online" : "Down"}
          </div>
          <div className="stat-label">
            API ({health?.environment ?? "unknown"})
          </div>
        </div>
        <div className="stat-card">
          <div
            className={`health-pill ${readiness?.database === "up" ? "stat-green" : "stat-red"}`}
          >
            <span className="pulse" style={{ background: "currentColor" }} />
            {readiness?.database === "up" ? "Connected" : "Down"}
          </div>
          <div className="stat-label">Database</div>
        </div>
        <div className="stat-card">
          <div
            className={`health-pill ${readiness?.status === "ready" ? "stat-green" : "stat-amber"}`}
          >
            <span className="pulse" style={{ background: "currentColor" }} />
            {readiness?.status ?? "unknown"}
          </div>
          <div className="stat-label">Readiness</div>
        </div>
      </div>

      <h2 className="section-title">Business metrics</h2>
      <div className="stat-grid stat-grid-4">
        {FEATURED_METRICS.map(([name, label]) => {
          const value = findMetric(name);
          return (
            <div key={name} className="stat-card">
              <div className="stat-value">
                {value === null ? "—" : Math.round(value).toLocaleString()}
              </div>
              <div className="stat-label">{label}</div>
            </div>
          );
        })}
      </div>

      <div className="card">
        <div className="card-header-row">
          <h3>All Prometheus samples ({metricEntries.length})</h3>
          <button className="btn btn-small btn-ghost" onClick={() => setShowAll(!showAll)}>
            {showAll ? "Hide" : "Show"}
          </button>
        </div>
        {showAll && (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {metricEntries
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([name, value]) => (
                    <tr key={name}>
                      <td className="mono">{name}</td>
                      <td className="amount">{value.toLocaleString()}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

import { useCallback, useEffect, useState } from "react";
import {
  dismissTask,
  getDlqStats,
  listAllFailedTasks,
  requeueTask,
  scheduleTaskRetry,
} from "../api/endpoints";
import type { FailedTask, FailedTaskStatus, RetryQueueStats } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { StatusBadge } from "../components/StatusBadge";

const FILTERS: (FailedTaskStatus | "ALL")[] = [
  "ALL",
  "PENDING",
  "RETRYING",
  "DEAD",
  "RECOVERED",
];

export function DlqPage() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<FailedTask[]>([]);
  const [stats, setStats] = useState<RetryQueueStats | null>(null);
  const [filter, setFilter] = useState<FailedTaskStatus | "ALL">("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const isAdmin = user?.role === "admin";

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [taskList, statData] = await Promise.all([
        listAllFailedTasks(filter === "ALL" ? undefined : filter),
        getDlqStats(),
      ]);
      setTasks(taskList);
      setStats(statData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load DLQ");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  const act = async (fn: () => Promise<unknown>, msg: string) => {
    try {
      await fn();
      setNotice(msg);
      setError(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operation failed");
    }
  };

  if (loading && tasks.length === 0) {
    return <div className="page-loading">Loading dead-letter queue…</div>;
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <div className="eyebrow">Operations</div>
          <h1>Dead-Letter Queue</h1>
          <p className="page-subtitle">
            Background tasks that exhausted their retries. Nothing here is
            lost — requeue, reschedule, or dismiss with full context.
          </p>
        </div>
        <button className="btn btn-ghost" onClick={load}>
          Refresh
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {notice && <div className="alert alert-success">{notice}</div>}

      {stats && (
        <div className="stat-grid stat-grid-5">
          <div className="stat-card">
            <div className="stat-value">{stats.total}</div>
            <div className="stat-label">Total</div>
          </div>
          <div className="stat-card">
            <div className="stat-value stat-amber">{stats.pending}</div>
            <div className="stat-label">Pending</div>
          </div>
          <div className="stat-card">
            <div className="stat-value stat-blue">{stats.retrying}</div>
            <div className="stat-label">Retrying</div>
          </div>
          <div className="stat-card">
            <div className="stat-value stat-red">{stats.dead}</div>
            <div className="stat-label">Dead</div>
          </div>
          <div className="stat-card">
            <div className="stat-value stat-green">{stats.recovered}</div>
            <div className="stat-label">Recovered</div>
          </div>
        </div>
      )}

      <div className="toolbar">
        {FILTERS.map((f) => (
          <button
            key={f}
            className={`btn btn-small ${filter === f ? "btn-primary" : "btn-ghost"}`}
            onClick={() => setFilter(f)}
          >
            {f}
          </button>
        ))}
      </div>

      {tasks.length === 0 ? (
        <div className="empty-state">
          <h2>Queue is clear</h2>
          <p>No failed tasks match this filter. That's the goal.</p>
        </div>
      ) : (
        <div className="dlq-list">
          {tasks.map((task) => (
            <div key={task.id} className="card dlq-card">
              <div className="dlq-head">
                <div>
                  <span className="mono dlq-task-name">{task.task_name}</span>{" "}
                  <StatusBadge status={task.status} />
                </div>
                <span className="muted">
                  Failed {new Date(task.failed_at).toLocaleString()}
                </span>
              </div>
              <div className="dlq-error">
                <span className="badge badge-gray">{task.error_type}</span>
                <span>{task.error_message}</span>
              </div>
              <div className="dlq-meta">
                <span>
                  Retries: {task.retry_count}/{task.max_retries}
                </span>
                {task.next_retry_at && (
                  <span>
                    Next retry: {new Date(task.next_retry_at).toLocaleString()}
                  </span>
                )}
                {task.recovered_at && (
                  <span>
                    Recovered: {new Date(task.recovered_at).toLocaleString()}
                  </span>
                )}
              </div>
              {isAdmin && task.status !== "RECOVERED" && (
                <div className="action-row-compact">
                  <button
                    className="btn btn-small btn-primary"
                    onClick={() =>
                      act(() => requeueTask(task.id), "Task requeued for immediate retry")
                    }
                  >
                    Requeue Now
                  </button>
                  <button
                    className="btn btn-small"
                    onClick={() =>
                      act(
                        () => scheduleTaskRetry(task.id),
                        "Exponential-backoff retry scheduled",
                      )
                    }
                  >
                    Schedule Retry
                  </button>
                  <button
                    className="btn btn-small btn-danger"
                    onClick={() => {
                      if (window.confirm("Dismiss this task permanently?")) {
                        act(() => dismissTask(task.id), "Task dismissed");
                      }
                    }}
                  >
                    Dismiss
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from prometheus_client import Counter
    from prometheus_client import Gauge
    from prometheus_client import Histogram
    from prometheus_client import Summary
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False

if not _PROMETHEUS_AVAILABLE:
    class _Noop:
        def __init__(self, *args, **kwargs):
            pass
        def inc(self, *a, **kw): pass
        def dec(self, *a, **kw): pass
        def set(self, *a, **kw): pass
        def observe(self, *a, **kw): pass
        def labels(self, *a, **kw): return self
        def time(self): return self
        def __enter__(self): return self
        def __exit__(self, *a): pass

    Counter = Gauge = Histogram = Summary = _Noop  # type: ignore[misc,assignment]


# ── Claim throughput ───────────────────────────────────────────────────────────
claims_created_total = Counter(
    "claims_created_total",
    "Total number of insurance claims created",
)

claims_by_status_total = Counter(
    "claims_by_status_total",
    "Claim workflow transitions by status",
    ["status"],
)

# ── Workflow health ────────────────────────────────────────────────────────────
workflow_transitions_total = Counter(
    "workflow_transitions_total",
    "Total workflow state transitions",
    ["from_status", "to_status"],
)

workflow_failures_total = Counter(
    "workflow_failures_total",
    "Total failed workflow transitions",
)

# ── Fraud metrics ──────────────────────────────────────────────────────────────
fraud_checks_total = Counter(
    "fraud_checks_total",
    "Total fraud analysis runs",
)

fraud_high_risk_total = Counter(
    "fraud_high_risk_total",
    "Claims flagged as HIGH risk",
)

fraud_risk_by_level_total = Counter(
    "fraud_risk_by_level_total",
    "Fraud checks grouped by risk level",
    ["risk_level"],
)

# ── Payout / settlement ────────────────────────────────────────────────────────
payouts_initiated_total = Counter(
    "payouts_initiated_total",
    "Total payout settlements initiated",
)

payouts_completed_total = Counter(
    "payouts_completed_total",
    "Total payout settlements completed successfully",
)

payouts_failed_total = Counter(
    "payouts_failed_total",
    "Total payout settlements that failed",
)

payout_retry_total = Counter(
    "payout_retry_total",
    "Total payout retries triggered",
)

# ── Task / DLQ ─────────────────────────────────────────────────────────────────
failed_tasks_total = Counter(
    "failed_tasks_total",
    "Total tasks routed to dead-letter queue",
    ["task_name"],
)

dlq_depth = Gauge(
    "dlq_depth",
    "Current number of tasks in DEAD status",
)

# ── HTTP request latency ───────────────────────────────────────────────────────
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request processing time",
    ["method", "path", "status_code"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status_code"],
)

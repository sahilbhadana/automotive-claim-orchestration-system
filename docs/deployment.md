# Deployment Guide

## Prerequisites

- Docker 24+ and Docker Compose v2
- Git

## Quick Start (Docker Compose)

```bash
git clone <repo-url>
cd insurance-clain-wf

# Copy and configure environment
cp .env.example .env
# Edit JWT_SECRET_KEY and database credentials

docker compose up -d
```

Services start on:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **RabbitMQ Management**: http://localhost:15672 (claims / claims_secret)
- **Prometheus**: http://localhost:9090

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL DSN |
| `JWT_SECRET_KEY` | Yes | change-this | HS256 signing key |
| `CELERY_BROKER_URL` | Yes | redis://redis:6379/0 | Celery broker |
| `CELERY_RESULT_BACKEND` | Yes | redis://redis:6379/1 | Task result store |
| `AMQP_URL` | No | None | RabbitMQ for domain events |
| `RATE_LIMIT_DEFAULT` | No | 200 | Requests per window |
| `RATE_LIMIT_AUTH` | No | 20 | Auth endpoint limit |
| `RATE_LIMIT_WINDOW_SECONDS` | No | 60 | Sliding window size |

## Production Checklist

- [ ] Set a cryptographically random `JWT_SECRET_KEY` (≥ 32 bytes)
- [ ] Use separate PostgreSQL credentials for API and worker
- [ ] Enable SSL on PostgreSQL (`?sslmode=require`)
- [ ] Configure `AMQP_URL` for durable event publishing
- [ ] Set `APP_ENV=production` to enable JSON-formatted logs
- [ ] Mount Prometheus at `/api/v1/metrics` in your scrape config
- [ ] Set up log aggregation (Loki, CloudWatch, Datadog)
- [ ] Configure replica count for the worker service (≥ 2)

## Scaling Workers

```bash
# Scale Celery workers
docker compose up -d --scale worker=4
```

Workers are stateless and can be scaled horizontally. Each worker
consumes tasks from the shared Redis queue.

## Running Migrations

The application uses SQLAlchemy `create_all()` at startup. For production,
migrate to Alembic:

```bash
pip install alembic
alembic init alembic
# Configure alembic.ini to use $DATABASE_URL
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Run specific test categories:

```bash
pytest tests/unit/ -v          # Fast, no DB required
pytest tests/integration/ -v   # Requires SQLite (in-memory)
pytest tests/simulation/ -v    # Chaos and failure tests
```

## Health & Readiness Probes

```
GET /api/v1/health   → {"status": "ok", ...}
GET /api/v1/ready    → {"status": "ready"|"degraded", "database": "up"|"down"}
```

Use `ready` for Kubernetes `readinessProbe` and `health` for `livenessProbe`.

## Observability

### Prometheus Metrics

Import the provided `prometheus.yml` or add a scrape job:

```yaml
- job_name: claim_api
  static_configs:
    - targets: ["<api-host>:8000"]
  metrics_path: /api/v1/metrics
```

### Key Dashboards to Build

| Panel | Query |
|---|---|
| Claims/min | `rate(claims_created_total[1m]) * 60` |
| Fraud HIGH % | `fraud_high_risk_total / fraud_checks_total * 100` |
| Failed workflows | `rate(workflow_failures_total[5m])` |
| DLQ depth | `dlq_depth` |
| P99 latency | `histogram_quantile(0.99, http_request_duration_seconds_bucket)` |
| Payout success rate | `payouts_completed_total / payouts_initiated_total * 100` |

### Structured Log Fields

Every log line is a JSON object with:

```json
{
  "timestamp": "2026-06-10T10:30:00Z",
  "level": "INFO",
  "logger": "app.access",
  "message": "HTTP request",
  "http_method": "POST",
  "http_path": "/api/v1/claims",
  "http_status": 201,
  "duration_ms": 42.1,
  "correlation_id": "uuid",
  "request_id": "uuid"
}
```

## Dead-Letter Queue Operations

The DLQ stores Celery task failures with exponential backoff metadata.

```bash
# View dead tasks (admin role required)
GET /api/v1/dlq

# Requeue a specific dead task
POST /api/v1/dlq/{task_id}/retry

# View stats
GET /api/v1/dlq/stats

# Schedule exponential-backoff retry
POST /api/v1/dlq/{task_id}/schedule-retry
```

## Docker Image

```bash
docker build -t insurance-claim-api:latest .
docker run -p 8000:8000 --env-file .env insurance-claim-api:latest
```

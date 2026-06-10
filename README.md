# Insurance Claim Workflow Orchestration System

A **production-grade** FastAPI backend for end-to-end automotive insurance claim processing. Handles the full claim lifecycle: submission, fraud detection, adjuster assignment, repair estimation, settlement, and payout — with enterprise-class reliability, observability, and event-driven architecture.

---

## ✨ What It Does

The system manages every stage of an insurance claim:

1. **Claim Intake** — Register new claims with policy, vehicle, and incident details
2. **Document Verification** — Accept and validate accident photos, FIR, and vehicle registration
3. **Policy Validation** — Check coverage eligibility, effective dates, and policy status
4. **Fraud Analysis** — Apply rule-based scoring for duplicate claims, repeated patterns, high-risk garages, and suspicious repair costs
5. **Adjuster Assignment** — Allocate claims to adjusters using geographic proximity, expertise level, and workload balancing
6. **Repair Estimation** — Manage garage quotations with supervisor approval/rejection workflows
7. **Final Approval** — Supervisors approve or reject claims with audit trail
8. **Payout Settlement** — Initiate bank transfers with automatic exponential-backoff retry and reversal support
9. **Audit & Notifications** — Immutable activity timeline and email/SMS lifecycle communications

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION (Port 8000)              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          MIDDLEWARE STACK                                │  │
│  │  • CorrelationID (request tracing)                       │  │
│  │  • Rate Limiter (200 req/min, 20 for auth)              │  │
│  │  • Request Tracer (structured access logs)              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         │                                       │
│  ┌──────────┬──────────┬──────────┬───────────────────────┐    │
│  ▼          ▼          ▼          ▼                       ▼    │
│ Claims  Workflow   Fraud    Settlements   DLQ            │    │
│ Routes  Routes     Routes   Routes        Routes          │    │
│                                                            │    │
│ Policies Adjusters Garages  Documents    Auth            │    │
│ Routes   Routes     Routes    Routes      Routes          │    │
└─────────────────────────────────────────────────────────────────┘
              ┌─────────┬──────────┬──────────────────┐
              ▼         ▼          ▼                  ▼
        PostgreSQL  Redis 7   RabbitMQ 3.13    Prometheus 2.5
         (16 Alpine) (Broker)  (Events)         (Metrics)
              │         │          │
              ▼         ▼          ▼
        Claims     Celery     Domain Events
        State      Result      (topic: claim.*)
        + Audit    Backend

┌──────────────────────────────────────────────────────────┐
│         CELERY WORKER POOL (Horizontally scalable)       │
│                                                          │
│  claims.validate_images          ← Document validation  │
│  claims.run_fraud_checks         ← Risk scoring        │
│  claims.assign_adjuster          ← Geo + workload      │
│  claims.execute_workflow         ← State transitions    │
│  claims.send_notification        ← Email/SMS dispatch   │
│  settlements.process_payout      ← Bank gateway sim     │
│  settlements.retry_pending       ← Retry sweep (cron)   │
│                                                          │
│  All tasks: ResilientTask base + DLQ routing           │
└──────────────────────────────────────────────────────────┘
```

---

## 🚀 Core Features

### Resilience & Reliability 

- **Dead-Letter Queue (DLQ)** — Every Celery task failure is persisted to the `failed_tasks` table with full context
- **Exponential Backoff Retry** — Base 2s (30s for settlements), doubles each retry, capped at 300s
- **Task Resilience** — `ResilientTask` base class auto-routes unhandled exceptions to DLQ instead of dropping them
- **Payout Retry Logic** — Settlement failures schedule automatic retries; manual requeue via admin API
- **Admin DLQ Interface** — `/api/v1/dlq` endpoints: view dead tasks, stats, requeue, schedule retry, dismiss

### Event-Driven Architecture

- **RabbitMQ Topic Exchange** — `insurance.claims` publishes domain events
- **Routing Keys**:
  - `claim.created` — when a new claim is submitted
  - `claim.fraud.completed` — fraud analysis results
  - `claim.approved` — claim approved by supervisor
  - `claim.payout.initiated` — payout settlement started
- **Graceful Fallback** — If RabbitMQ is unavailable, events are logged as JSON and queued (no hard dependency)
- **Correlation IDs** — All events carry `correlation_id` for distributed request tracing

### Payout Settlement & Retry

- **Settlement Model** — Full state machine: `INITIATED → PROCESSING → COMPLETED/FAILED → REVERSED`
- **Simulated Bank Gateway** — Payout succeeds on even retry counts, fails on odd (demo behavior; swap with real API)
- **Automatic Retry Scheduling** — Exponential backoff: 30s, 60s, 120s; max 3 retries
- **Reversal Support** — Reverse a completed settlement for chargebacks/disputes
- **Settlement Endpoints**:
  - `POST /api/v1/claims/{claim_id}/settlements` — initiate payout
  - `GET /api/v1/claims/{claim_id}/settlements` — list all payouts
  - `POST /api/v1/settlements/{settlement_id}/retry` — retry failed settlement
  - `POST /api/v1/settlements/{settlement_id}/reverse` — reverse completed settlement

### Observability & Monitoring

- **Structured JSON Logging** — Every log is a single-line JSON object (timestamp, level, correlation_id, duration_ms, exception)
- **Production Format** — Set `APP_ENV=production` to enable JSON; dev mode uses human-readable format
- **Prometheus Metrics** (15 total):
  - `claims_created_total` — claim submission rate
  - `workflow_transitions_total{from_status, to_status}` — state machine transitions
  - `fraud_high_risk_total` — claims flagged HIGH risk
  - `fraud_risk_by_level_total{risk_level}` — fraud distribution (LOW/MEDIUM/HIGH)
  - `payouts_initiated_total / completed_total / failed_total` — settlement metrics
  - `payout_retry_total` — retry triggers
  - `dlq_depth` — current dead-letter queue size
  - `http_request_duration_seconds{method, path, status_code}` — latency histogram
  - `http_requests_total{method, path, status_code}` — request count
- **Metrics Endpoints**:
  - `GET /api/v1/metrics` — Prometheus text format (scrape-friendly)
  - `GET /api/v1/metrics/summary` — JSON snapshot for dashboards

### API Gateway & Rate Limiting

- **Correlation ID Middleware** — Mints `X-Correlation-ID` per request; echoes client-supplied values
- **Request ID** — Each request gets a unique `X-Request-ID` for hop-by-hop tracing
- **Sliding-Window Rate Limiter**:
  - Default: **200 requests per 60 seconds**
  - Auth endpoints: **20 requests per 60 seconds** (tighter)
  - Returns `429 Too Many Requests` with `Retry-After` header
- **Rate Limit Headers** — `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Window`
- **Request Tracer** — Structured access log with method, path, status, duration_ms, correlation_id, client IP
- **CORS** — Enabled for all origins (configure in production)

### Testing & Validation

Three test layers with **~50 test cases**:

1. **Unit Tests** (`tests/unit/`) — Fast, in-memory SQLite, zero external deps:
   - `test_retry_service` — exponential backoff math, DLQ lifecycle
   - `test_workflow_service` — state machine transitions, terminal state detection
   - `test_settlement_service` — backoff delay, retry exhaustion, reversal validation
   - `test_fraud_service` — rule engine, risk-level thresholds

2. **Integration Tests** (`tests/integration/`) — FastAPI TestClient with full HTTP layer:
   - `test_claim_workflow` — health/ready probes, OpenAPI schema structure, auth flow, rate-limit headers
   - `test_settlement_workflow` — full payout lifecycle, pending-retry discovery, payment methods

3. **Failure Simulation** (`tests/simulation/`) — Chaos & edge cases:
   - Invalid workflow transitions
   - DLQ accumulation under exhausted retries
   - Duplicate settlement blocking
   - Event publisher graceful fallback (AMQP absent)

Run all tests:
```bash
pytest tests/ -v
```

### Production Readiness

- **GitHub Actions CI** — Lint (ruff), typecheck (mypy), test (unit/integration/simulation), Docker build with cache, OpenAPI schema export
- **Architecture Documentation** — Full system diagram, state machine flowchart, design decision table
- **Deployment Guide** — Quick-start, environment variables, production checklist, scaling, Prometheus queries, DLQ runbook
- **Postman Collection** — Full workflow with auto-token-capture, request folders for each domain, collection variables
- **OpenAPI / Swagger** — Self-documenting API at `/docs` with interactive examples

---

## 🛠️ Technology Stack

| Component | Version | Purpose |
|---|---|---|
| **FastAPI** | 0.116 | Web framework |
| **SQLAlchemy** | 2.0 | ORM |
| **PostgreSQL** | 16 (Alpine) | Persistent state |
| **Redis** | 7 (Alpine) | Celery broker + result backend |
| **Celery** | 5.5 | Task queue |
| **RabbitMQ** | 3.13 (Management UI) | Event bus |
| **Prometheus** | 2.5 | Metrics collection |
| **PyJWT** | 2.10 | Token signing |
| **Passlib/bcrypt** | 1.7 | Password hashing |
| **Pydantic** | 2.x | Data validation |
| **Pytest** | 8.3 | Test framework |

---

## ⚡ Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/sahilbhadana/automotive-claim-orchestration-system.git
cd insurance-clain-wf

cp .env.example .env
# Edit .env if desired (default creds: claims_user / claims_password)
```

### 2. Start All Services

```bash
docker compose up -d
```

Wait ~30 seconds for all services to become healthy:

```bash
docker compose ps
```

Expected output:
```
claim-api          ✓ running
claim-worker       ✓ running
claim-postgres     ✓ healthy
claim-redis        ✓ healthy
claim-rabbitmq     ✓ healthy
claim-prometheus   ✓ running
```

### 3. Verify Health

```bash
curl http://localhost:8000/api/v1/health
# {"status": "ok", "service": "...", "environment": "development"}

curl http://localhost:8000/api/v1/ready
# {"status": "ready", "database": "up"}
```

### 4. Open Swagger UI

**http://localhost:8000/docs**

Register, log in, and create your first claim!

---

## 📊 Full API Reference

### Health & Observability

- `GET /api/v1/health` — Service health
- `GET /api/v1/ready` — Readiness probe (database status)
- `GET /api/v1/metrics` — Prometheus text format
- `GET /api/v1/metrics/summary` — JSON snapshot

### Authentication

- `POST /api/v1/auth/register` — Register new user
- `POST /api/v1/auth/login` — Obtain JWT token
- `GET /api/v1/auth/me` — Current user profile

### Claims Lifecycle

- `POST /api/v1/claims` — Create claim
- `GET /api/v1/claims` — List all claims
- `GET /api/v1/claims/{claim_id}` — Get claim details
- `PATCH /api/v1/claims/{claim_id}/status` — Update status
- `GET /api/v1/claims/{claim_id}/workflow` — Current state + allowed transitions
- `POST /api/v1/claims/{claim_id}/workflow/execute` — Advance workflow

### Fraud Analysis

- `POST /api/v1/claims/{claim_id}/fraud/analyze` — Run fraud checks

### Documents

- `POST /api/v1/claims/{claim_id}/documents` — Upload document
- `GET /api/v1/claims/{claim_id}/documents` — List documents
- `GET /api/v1/claims/{claim_id}/documents/{doc_id}` — Download document

### Policies

- `POST /api/v1/policies` — Create policy
- `GET /api/v1/policies` — List policies
- `GET /api/v1/policies/{policy_id}` — Get policy
- `POST /api/v1/policies/{policy_id}/validate-claim` — Validate claim eligibility

### Adjusters

- `POST /api/v1/adjusters` — Create adjuster
- `GET /api/v1/adjusters` — List adjusters
- `GET /api/v1/adjusters/{adjuster_id}` — Get adjuster details
- `POST /api/v1/adjusters/{adjuster_id}/assign` — Assign to claim

### Garages & Repair Estimates

- `POST /api/v1/garages` — Create garage
- `GET /api/v1/garages` — List garages
- `POST /api/v1/claims/{claim_id}/repair-estimates` — Submit repair estimate
- `GET /api/v1/claims/{claim_id}/repair-estimates` — List estimates
- `PATCH /api/v1/repair-estimates/{estimate_id}/approve` — Approve estimate

### Settlements & Payouts

- `POST /api/v1/claims/{claim_id}/settlements` — Initiate payout
- `GET /api/v1/claims/{claim_id}/settlements` — List settlements
- `GET /api/v1/settlements/{settlement_id}` — Get settlement details
- `POST /api/v1/settlements/{settlement_id}/retry` — Retry failed settlement
- `POST /api/v1/settlements/{settlement_id}/reverse` — Reverse completed settlement

### Dead-Letter Queue (Admin Only)

- `GET /api/v1/dlq` — List dead tasks
- `GET /api/v1/dlq/all?status=DEAD` — All failed tasks by status
- `GET /api/v1/dlq/stats` — DLQ statistics
- `POST /api/v1/dlq/{task_id}/retry` — Requeue a dead task
- `POST /api/v1/dlq/{task_id}/schedule-retry` — Manually schedule exponential-backoff retry
- `DELETE /api/v1/dlq/{task_id}` — Dismiss task from queue

### Audit & Notifications

- `GET /api/v1/claims/{claim_id}/activity` — Claim activity timeline
- `POST /api/v1/claims/{claim_id}/notifications/dispatch` — Send notification

### Verification

- `POST /api/v1/verifications/vehicle-driver` — Verify vehicle & driver

---

## 🧪 Testing

### Run All Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

**Expected: ~50 tests passing in ~2 minutes**

### Run Specific Test Categories

```bash
# Fast unit tests (no DB, ~30s)
pytest tests/unit/ -v

# Integration tests (full HTTP layer, ~1min)
pytest tests/integration/ -v

# Failure simulation & chaos tests (~30s)
pytest tests/simulation/ -v
```

### Test Coverage Report

```bash
pytest tests/ --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

---

## 📈 Monitoring & Observability

### Prometheus Dashboard

Open **http://localhost:9090** and query:

```promql
# Claims per minute
rate(claims_created_total[1m]) * 60

# Fraud HIGH risk percentage
fraud_high_risk_total / fraud_checks_total * 100

# Payout success rate
payouts_completed_total / payouts_initiated_total * 100

# DLQ depth (current dead tasks)
dlq_depth

# P99 HTTP latency
histogram_quantile(0.99, http_request_duration_seconds_bucket)
```

### Structured Logs

View logs in development:
```bash
docker compose logs api -f
```

Production logs are JSON-formatted and can be piped to Loki, CloudWatch, Datadog, etc.

### Request Tracing

Every response includes:
```
X-Correlation-ID: <uuid>     # Logical operation ID (echoed from client if provided)
X-Request-ID: <uuid>         # Physical request ID (always fresh per request)
```

Use these in application logs and downstream service calls to reconstruct request paths.

---

## 🚢 Deployment

See **`docs/deployment.md`** for:
- Production environment variables
- Production checklist (SSL, secrets rotation, log aggregation)
- Scaling workers horizontally
- Alembic migration path
- Health probe configuration (Kubernetes)
- DLQ operational runbook

**Quick deploy:**

```bash
# Set JWT_SECRET_KEY and database credentials in .env
docker compose -f docker-compose.yml up -d

# Monitor
docker compose logs -f api
```

---

## 📁 Project Structure

```
insurance-clain-wf/
├── app/
│   ├── api/                    # FastAPI routes
│   │   ├── claim_routes.py
│   │   ├── workflow_routes.py
│   │   ├── fraud_routes.py
│   │   ├── settlement_routes.py
│   │   ├── retry_routes.py
│   │   ├── metrics_routes.py
│   │   └── ...
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── metrics.py
│   ├── db/
│   │   └── session.py
│   ├── middleware/
│   │   ├── correlation_id.py
│   │   ├── rate_limiter.py
│   │   └── request_tracer.py
│   ├── models/
│   │   ├── claim.py
│   │   ├── settlement.py
│   │   ├── failed_task.py
│   │   └── ...
│   ├── services/
│   │   ├── retry_service.py
│   │   ├── settlement_service.py
│   │   ├── workflow_service.py
│   │   ├── fraud_service.py
│   │   └── ...
│   ├── schemas/
│   │   ├── retry.py
│   │   ├── settlement.py
│   │   └── ...
│   ├── tasks/
│   │   ├── claim_tasks.py        (updated with ResilientTask)
│   │   └── settlement_tasks.py
│   ├── workers/
│   │   ├── celery_app.py         (updated with settings)
│   │   └── base_task.py
│   ├── events/
│   │   ├── event_schemas.py
│   │   └── publisher.py
│   └── main.py                   (updated with middleware)
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── simulation/
│   ├── conftest.py
│   └── pytest.ini
├── .github/workflows/
│   └── ci.yml
├── docs/
│   ├── architecture.md
│   └── deployment.md
├── postman/
│   └── insurance_claims_api.json
├── .env.example                  (updated)
├── docker-compose.yml            (updated with RabbitMQ, Prometheus)
├── prometheus.yml
├── requirements.txt              (updated)
├── README.md                     (this file)
└── Dockerfile
```

---

## 🔄 Workflow State Machine

```
CLAIM_CREATED
    ↓
DOCUMENT_VERIFICATION  ← Validate accident photos
    ├→ REJECTED
    ↓
POLICY_VALIDATION      ← Check coverage
    ├→ REJECTED
    ↓
FRAUD_ANALYSIS         ← Risk scoring
    ├→ REJECTED (HIGH risk)
    ↓
ADJUSTER_ASSIGNMENT    ← Geographic + workload
    ↓
REPAIR_ESTIMATION      ← Garage quotation approval
    ├→ REJECTED
    ↓
FINAL_APPROVAL         ← Supervisor sign-off
    ├→ REJECTED
    ↓
APPROVED
    ↓
PAYOUT                 ← Settlement with retry logic (terminal)

REJECTED (terminal)
```

---

## 🔐 Authentication & Authorization

**Roles:**

| Role | Permissions |
|---|---|
| `customer` | Submit claims, upload documents |
| `adjuster` | View/process claims, run fraud checks, assign themselves |
| `supervisor` | Approve/reject repairs, approve/reject claims, manage payouts |
| `admin` | All + manage users, manage DLQ, view internal metrics |

**JWT Token:**

```bash
POST /api/v1/auth/register
{
  "email": "adjuster@example.com",
  "full_name": "Rahul Verma",
  "password": "SecurePass123!",
  "role": "adjuster"
}

POST /api/v1/auth/login
username: adjuster@example.com
password: SecurePass123!

# Returns:
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

**Using the token:**

```bash
curl -H "Authorization: Bearer eyJhbGc..." http://localhost:8000/api/v1/claims
```

---

## 🐛 Troubleshooting

### Services Won't Start

```bash
# Check service health
docker compose ps

# View logs
docker compose logs api
docker compose logs worker
docker compose logs postgres
```

### Tests Fail

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Run tests with verbose output
pytest tests/ -vvs

# Run specific test file
pytest tests/unit/test_retry_service.py -v
```

### Celery Tasks Not Running

```bash
# Check Redis is up
redis-cli ping
# Expected: PONG

# Check worker logs
docker compose logs worker -f

# Verify Celery broker is configured
echo $CELERY_BROKER_URL
```

### DLQ Accumulating

If tasks are piling up in the dead-letter queue:

1. Check worker logs for the underlying error
2. Fix the issue in the code
3. Use the DLQ API to requeue: `POST /api/v1/dlq/{task_id}/retry`

Or dismiss tasks that are unrecoverable: `DELETE /api/v1/dlq/{task_id}`

### Rate Limit Exceeded

If hitting rate limits during testing, increase in `.env`:

```
RATE_LIMIT_DEFAULT=500
RATE_LIMIT_AUTH=50
```

---

## 📚 Documentation

- **Architecture & Design**: `docs/architecture.md`
- **Deployment & Operations**: `docs/deployment.md`
- **API Reference**: Auto-generated at `/docs` (Swagger UI)
- **Postman Collection**: `postman/insurance_claims_api.json`
- **CI/CD Pipeline**: `.github/workflows/ci.yml`

---

## 📝 License

Apache 2.0

---

## 🤝 Support

For questions or issues:
1. Check `docs/deployment.md` for operational guides
2. Review test cases in `tests/` for usage examples
3. Open an issue on GitHub with logs and reproduction steps

---

**Built with ❤️ for enterprise insurance claim processing.**

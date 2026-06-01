# Automotive Claim Orchestration System

Automotive Claim Orchestration System is a production-style backend platform for end-to-end insurance claim processing. It models the claim lifecycle as a workflow, coordinates validation and fraud analysis, manages evidence and repair estimates, assigns adjusters, records audit history, and dispatches asynchronous background work through Celery.

## What it does

- manages automotive insurance claims from intake through payout
- enforces workflow state transitions across the claim lifecycle
- validates policies, vehicles, driver identity, and supporting documents
- runs fraud analysis rules for duplicate claims, repeated incidents, high-risk garages, and suspicious repair costs
- assigns adjusters dynamically using geography, expertise, and workload
- supports garage quotation submission and repair estimate approval decisions
- stores immutable audit logs and exposes a claim activity timeline
- dispatches email and SMS-style notifications from workflow events
- protects sensitive operations with JWT authentication and role-based authorization

## Core capabilities

- Claim management: create, fetch, list, and update claims with UUID identifiers and persisted lifecycle state
- Workflow orchestration: inspect workflow state, execute transitions, and trigger downstream async jobs
- Policy validation: check coverage eligibility, insured vehicle match, effective dates, and policy status
- Verification engine: validate vehicle registration, driving license format, and ownership consistency
- Document service: upload accident photos, FIR records, and RC documents with type and size validation
- Fraud engine: apply suspicious-claim rules and produce structured fraud analysis results
- Adjuster assignment: allocate claims using city match, expertise level, and pending workload
- Repair estimation: manage garages, claim-linked estimates, and approval or rejection of quotations
- Audit logging: persist append-only activity records for claim actions and workflow events
- Notification engine: send templated lifecycle communications through email and SMS abstractions
- Background processing: execute fraud checks, image validation, workflow actions, and notifications through Celery
- Access control: issue JWT access tokens and enforce role-based route protection for `customer`, `adjuster`, `supervisor`, and `admin`

## Architecture

```text
FastAPI API Layer
  -> Workflow Orchestration
  -> Claim / Policy / Verification / Fraud / Garage / Adjuster Services
  -> Audit Logging + Notification Engine
  -> Celery Background Tasks

PostgreSQL
Redis
Local Document Storage
Docker Compose Runtime
```

## Technology stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Celery
- Docker Compose
- JWT authentication

## Getting started

1. Copy `.env.example` to `.env`
2. Start the application stack:

```bash
docker compose up --build
```

3. Open the API documentation:

- Swagger UI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`
- Readiness: `http://localhost:8000/api/v1/ready`

## Authentication

Register a user and obtain a JWT token before using protected routes.

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

Role model:

- `customer`: claim submission and evidence-oriented access
- `adjuster`: operational claim processing access
- `supervisor`: workflow control, fraud review, notifications, and approvals
- `admin`: full administrative access

## Key API areas

- Claims: `/api/v1/claims`
- Workflow: `/api/v1/claims/{claim_id}/workflow`
- Documents: `/api/v1/claims/{claim_id}/documents`
- Policies: `/api/v1/policies`
- Verification: `/api/v1/verifications/vehicle-driver`
- Fraud analysis: `/api/v1/claims/{claim_id}/fraud/analyze`
- Adjusters: `/api/v1/adjusters`
- Garages: `/api/v1/garages`
- Repair estimates: `/api/v1/claims/{claim_id}/repair-estimates`
- Audit timeline: `/api/v1/claims/{claim_id}/activity`
- Notifications: `/api/v1/claims/{claim_id}/notifications/dispatch`
- Async tasks: `/api/v1/tasks/{task_id}`

## Project structure

```text
app/
  api/
  core/
  db/
  models/
  schemas/
  services/
  tasks/
  workers/
  main.py
```

## Notes

- The system currently uses local document storage and can be extended to object storage later.
- Background tasks run through the Celery worker defined in `docker-compose.yml`.
- Audit events are written from core workflow mutations so claim history can be reconstructed from the activity timeline.

# Automotive Insurance Claim Workflow Orchestration System

Production-style distributed backend system for end-to-end automotive insurance claim processing using event-driven workflows, async processing, fraud detection, document management, and operational observability.

## Day 1 Scope

This repository currently includes:

- FastAPI application bootstrap
- environment-driven configuration
- PostgreSQL development container
- Docker Compose setup
- health and readiness endpoints
- claim domain model with lifecycle status persistence
- claim creation, retrieval, listing, and status update APIs
- policy lookup and coverage eligibility validation APIs
- vehicle registration and driver verification APIs

## Run locally

1. Copy `.env.example` to `.env`
2. Start the stack:

```bash
docker compose up --build
```

3. Open:

- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`
- Readiness: `http://localhost:8000/api/v1/ready`
- Claims: `http://localhost:8000/api/v1/claims`
- Policies: `http://localhost:8000/api/v1/policies`
- Verifications: `http://localhost:8000/api/v1/verifications/vehicle-driver`

## Initial structure

```text
app/
  api/
  core/
  db/
  models/
  schemas/
  services/
  main.py
```

This foundation is intentionally small so later days can add workflow orchestration, event publishing, fraud checks, document handling, and payout processing without reshaping the repo.

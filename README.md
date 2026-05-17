# Automotive Insurance Claim Workflow Orchestration System

Production-style distributed backend system for end-to-end automotive insurance claim processing using event-driven workflows, async processing, fraud detection, document management, and operational observability.

## Day 1 Scope

This repository currently includes:

- FastAPI application bootstrap
- environment-driven configuration
- PostgreSQL development container
- Docker Compose setup
- health and readiness endpoints

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

## Initial structure

```text
app/
  api/
  core/
  db/
  main.py
```

This foundation is intentionally small so later days can add workflow orchestration, event publishing, fraud checks, document handling, and payout processing without reshaping the repo.


# System Architecture

## Overview

The Insurance Claim Workflow Orchestration System is a production-grade FastAPI backend that coordinates the full lifecycle of automotive insurance claims — from initial submission through fraud detection, adjuster assignment, repair estimation, and final payout settlement.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT TIER                                  │
│          Mobile App  /  Web Portal  /  Internal Tools               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API GATEWAY LAYER                               │
│  CorrelationID Middleware → Rate Limiter → Request Tracer            │
│  CORSMiddleware → JWT Auth → Role-Based Authorization                │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION (Port 8000)                   │
│                                                                      │
│  ┌──────────┐  ┌─────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │  Claims  │  │ Workflow│  │  Fraud   │  │   Settlements &    │  │
│  │  Routes  │  │  Routes │  │  Routes  │  │   Payout Routes    │  │
│  └──────────┘  └─────────┘  └──────────┘  └────────────────────┘  │
│  ┌──────────┐  ┌─────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ Policies │  │Adjusters│  │  Garages │  │  DLQ / Retry API   │  │
│  │  Routes  │  │  Routes │  │  Routes  │  │   (Admin Only)     │  │
│  └──────────┘  └─────────┘  └──────────┘  └────────────────────┘  │
│  ┌──────────┐  ┌─────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ Auth     │  │ Audit   │  │Documents │  │  /metrics          │  │
│  │ Routes   │  │ Routes  │  │  Routes  │  │  (Prometheus)      │  │
│  └──────────┘  └─────────┘  └──────────┘  └────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────┘
              ┌────────────┼────────────┐
              ▼            ▼            ▼
┌─────────────────┐  ┌──────────┐  ┌──────────────────────────────┐
│   PostgreSQL 16 │  │ Redis 7  │  │        RabbitMQ 3.13         │
│                 │  │          │  │                              │
│  claims         │  │ Celery   │  │  Exchange: insurance.claims  │
│  policies       │  │ Broker   │  │  Routing Keys:               │
│  adjusters      │  │ + Result │  │  · claim.created             │
│  garages        │  │ Backend  │  │  · claim.fraud.completed     │
│  documents      │  │          │  │  · claim.approved            │
│  settlements    │  │          │  │  · claim.payout.initiated    │
│  failed_tasks   │  │          │  └──────────────────────────────┘
│  audit_logs     │  │          │
└─────────────────┘  └──────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CELERY WORKER POOL                                │
│                                                                      │
│  claims.validate_images     → Document validation                   │
│  claims.run_fraud_checks    → Fraud rule engine                     │
│  claims.assign_adjuster     → Geographic assignment algorithm       │
│  claims.execute_workflow    → State machine transitions             │
│  claims.send_notification   → Email/SMS dispatch                   │
│  settlements.process_payout → Bank gateway simulation              │
│  settlements.retry_pending  → Periodic retry sweep                 │
│                                                                      │
│  All tasks: ResilientTask base → exponential backoff + DLQ routing │
└─────────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        OBSERVABILITY                                  │
│                                                                      │
│  Prometheus (:9090)  ←  /api/v1/metrics scrape (10s interval)      │
│  Structured JSON logs → stdout → log aggregator (Loki/CloudWatch)  │
│                                                                      │
│  Key metrics tracked:                                               │
│  · claims_created_total                                             │
│  · workflow_transitions_total{from_status, to_status}              │
│  · fraud_risk_by_level_total{risk_level}                           │
│  · payouts_completed_total / payouts_failed_total                  │
│  · dlq_depth (gauge)                                               │
│  · http_request_duration_seconds{method, path, status_code}       │
└─────────────────────────────────────────────────────────────────────┘
```

## Claim Workflow State Machine

```
         ┌─────────────────┐
         │  CLAIM_CREATED  │  ← POST /api/v1/claims
         └────────┬────────┘
                  │
                  ▼
    ┌─────────────────────────┐
    │  DOCUMENT_VERIFICATION  │  ← Celery: validate_images_task
    └──────┬──────────────────┘
           │               │
     PASS  │          FAIL │
           ▼               ▼
┌──────────────────┐    ┌──────────┐
│ POLICY_VALIDATION│    │ REJECTED │ (terminal)
└──────┬───────────┘    └──────────┘
       │               │
 VALID │         LAPSED│
       ▼               ▼
┌────────────────┐   REJECTED
│ FRAUD_ANALYSIS │  ← Celery: run_fraud_checks_task
└──────┬─────────┘     │ HIGH_RISK → REJECTED
       │ LOW/MED
       ▼
┌─────────────────────┐
│ ADJUSTER_ASSIGNMENT │  ← Celery: assign_adjuster_task (geo + expertise)
└──────┬──────────────┘
       │
       ▼
┌──────────────────┐
│ REPAIR_ESTIMATION│  ← Garage submits quotation
└──────┬───────────┘
       │               │ REJECT
       ▼               ▼
┌──────────────┐    REJECTED
│ FINAL_APPROVAL│
└──────┬────────┘
       │ APPROVE
       ▼
  ┌──────────┐
  │ APPROVED │  ← RabbitMQ: ClaimApproved event published
  └────┬─────┘
       │
       ▼
  ┌────────┐
  │ PAYOUT │  ← Settlement service + payout retry pipeline
  └────────┘    (terminal)
```

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Async task queue | Celery + Redis | Proven at scale; Redis doubles as result backend |
| Event bus | RabbitMQ + topic exchange | Decouples producers from consumers; durable routing |
| Event fallback | Structured log-only | Graceful degradation when AMQP unavailable |
| Rate limiting | In-process sliding window | No external dep; restart-safe with Redis migration path |
| DLQ | PostgreSQL table | Queryable, auditable, survives worker restarts |
| Payout retry | Exponential backoff (30s base, 600s cap) | Mirrors industry gateway retry SLAs |
| Auth | JWT HS256, 120min TTL | Stateless; role claims embedded in token |
| Observability | Prometheus + structured JSON | Standard cloud-native stack |

## Services

| Service | Responsibility |
|---|---|
| `claim_service` | CRUD + status transitions |
| `workflow_service` | State machine enforcement |
| `fraud_service` | Rule-based risk scoring |
| `adjuster_service` | Geographic + workload assignment |
| `garage_service` | Repair estimate approval pipeline |
| `policy_service` | Coverage validation |
| `settlement_service` | Payout initiation + retry orchestration |
| `retry_service` | DLQ management + exponential backoff scheduling |
| `notification_service` | Email/SMS templating |
| `audit_service` | Immutable activity timeline |
| `verification_service` | Vehicle + driver identity checks |

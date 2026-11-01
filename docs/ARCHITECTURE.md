# Architecture

MentorHub is a **modular monolith**: one deployable API split into feature modules with
strict boundaries, plus background workers that share the same codebase. This keeps
operations simple (one service to deploy, one DB) while leaving a clean seam to extract a
module into its own service later if it ever needs to scale independently
(see [ADR-0001](adr/0001-modular-monolith.md)).

## Containers

```mermaid
flowchart LR
  user([Browser]) -->|HTTPS| web[Frontend<br/>Vue SPA on nginx]
  web -->|/api, /ws| api[API<br/>FastAPI x N replicas]
  api --> pg[(PostgreSQL 17<br/>pgvector + PostGIS)]
  api --> redis[(Redis<br/>cache · tokens · rate limits · pub/sub)]
  api -->|publish tasks| mq[[RabbitMQ]]
  mq --> worker[Celery workers<br/>queues: default · emails · ai]
  beat[Celery beat<br/>schedules] --> mq
  worker --> pg
  worker --> redis
  worker --> s3[(S3 storage<br/>RustFS / S3 / R2)]
  api -->|presigned URLs| s3
  worker --> smtp[SMTP<br/>Mailpit / provider]
  worker --> llm[LLM APIs<br/>Anthropic · OpenAI · Ollama]
  api --> llm
  api --> ext[Google Maps · reCAPTCHA · DocuSign]
  prom[Prometheus] -->|scrape /metrics| api
  graf[Grafana] --> prom
```

## Backend layers

```mermaid
flowchart TB
  R[router.py<br/>HTTP: parse, validate, status codes] --> S[service.py<br/>business rules, transactions, authz]
  S --> Rp[repository.py<br/>SQL queries]
  S --> P[integrations/ports.py<br/>Protocols]
  P -.implemented by.-> A[adapters<br/>S3, SMTP, LLM, Maps...]
  Rp --> DB[(PostgreSQL)]
  S --> T[tasks.py<br/>Celery, async side effects]
```

Dependencies point **inward**: routers know services, services know repositories and
ports, nothing below knows about HTTP. That makes services unit-testable with fakes and
lets adapters be swapped (e.g. reCAPTCHA → Turnstile) without touching business code.

## Data model (draft — evolves per phase)

```mermaid
erDiagram
  USER ||--o| MENTOR_PROFILE : has
  USER ||--o{ BOOKING : "books (mentee)"
  MENTOR_PROFILE ||--o{ BOOKING : "receives"
  MENTOR_PROFILE }o--o{ SKILL : teaches
  MENTOR_PROFILE ||--o{ AVAILABILITY_SLOT : defines
  BOOKING ||--o| REVIEW : "gets"
  BOOKING ||--o| CONTRACT : "signed via DocuSign"
  USER ||--o{ NOTIFICATION : receives
  MENTOR_PROFILE ||--o{ EMBEDDING_CHUNK : "indexed for RAG"
  KNOWLEDGE_DOC ||--o{ EMBEDDING_CHUNK : "chunked into"
  USER ||--o{ AI_CONVERSATION : has

  USER {
    uuid id PK
    citext email UK
    string hashed_password
    enum role
    bool is_active
  }
  MENTOR_PROFILE {
    uuid id PK
    uuid user_id FK
    text bio
    numeric hourly_rate
    geography location
  }
  BOOKING {
    uuid id PK
    uuid mentee_id FK
    uuid mentor_id FK
    tstzrange slot
    enum status
  }
  EMBEDDING_CHUNK {
    uuid id PK
    string source_type
    uuid source_id
    text content
    vector embedding
  }
```

## Cross-cutting concerns

| Concern | Where | Approach |
|---|---|---|
| Config | `core/config.py` | Typed `Settings` from env vars; refuses insecure defaults in prod |
| Errors | `core/exceptions.py` | Domain `AppError` → RFC 9457 Problem Details |
| Logging | `core/logging.py`, `core/middleware.py` | structlog, JSON in containers, `request_id` on every line |
| Metrics | `main.py` | Prometheus instrumentator: RPS, latency histograms, status classes |
| Health | `api/health.py` | `/health/live` (process) vs `/health/ready` (dependencies) |
| Pagination | `core/pagination.py` | Offset `Page[T]` for catalogs, keyset `CursorPage[T]` for feeds |
| Auth | `modules/auth` (Phase 1) | Short-lived JWT access + rotating refresh in Redis, RBAC dependencies |
| Caching | services (Phase 2) | Cache-aside in Redis, versioned keys, explicit invalidation |
| Background work | `worker/` | Celery, acks-late, idempotent tasks, separate queues by latency class |
| Real-time | `modules/notifications` (Phase 3) | WebSocket + Redis pub/sub fan-out, polling fallback |
| AI | `modules/ai` + ports (Phase 5) | Provider-agnostic LLM port, pgvector RAG, evals |

## Decisions

See [adr/](adr/) — each significant choice is recorded with context, alternatives and
consequences. They double as material for the thesis' design chapter.

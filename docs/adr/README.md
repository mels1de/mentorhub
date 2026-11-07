# Architecture Decision Records

Short documents explaining *why* the system looks the way it does. Format: context →
decision → alternatives → consequences. New decision = new file, never rewrite history
(supersede instead).

| # | Decision | Status |
|---|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith with vertical-slice modules | Accepted |
| [0002](0002-celery-rabbitmq.md) | Celery with RabbitMQ broker for background work | Accepted |
| [0003](0003-pgvector.md) | pgvector inside PostgreSQL for embeddings | Accepted |
| [0004](0004-s3-rustfs.md) | S3 API everywhere, RustFS for local development | Accepted |
| [0005](0005-auth-tokens.md) | Short-lived JWT + rotating refresh tokens in Redis | Accepted |
| [0006](0006-tooling.md) | Python 3.14 + uv, Vue 3 + TypeScript + TanStack Query | Accepted |
| [0007](0007-local-dev-workflow.md) | Local dev: backend + services in Docker, frontend on the host | Accepted |
| [0008](0008-settings-flat-env.md) | Typed settings from flat env vars and one root `.env` | Accepted |

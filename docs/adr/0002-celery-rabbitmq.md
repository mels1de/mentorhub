# 0002 — Celery with RabbitMQ for background work

**Context.** Emails, reminders, PDF/contract generation, embedding backfills and LLM
pipelines must not block HTTP requests; some are scheduled; failures must be retried.

**Decision.** Celery workers + Celery beat. RabbitMQ as broker (durable queues, acks,
dead-lettering, management UI), Redis as result backend. Queues split by latency class:
`default`, `emails`, `ai`. `acks_late` + idempotent tasks = at-least-once processing.

**Alternatives.** *FastAPI BackgroundTasks*: in-process, lost on crash, no retries or
scheduling. *Redis as broker*: fewer services, weaker delivery guarantees. *arq / Taskiq /
Dramatiq*: lighter and async-native, but Celery is the industry default, which matters for
the portfolio. *Kafka*: an event log, overkill for task queues here.

**Consequences.** Two extra containers. Celery tasks are sync functions; async code is
called via `asyncio.run` inside a task or through sync clients. Tasks must be idempotent.

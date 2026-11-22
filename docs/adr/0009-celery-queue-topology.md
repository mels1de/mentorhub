# 0009 — Celery queues: classic durable, routed by task-name prefix

**Context.** ADR-0002 chose Celery + RabbitMQ with queues `default`, `emails`, `ai`. We
still had to decide how tasks reach a queue, what delivery guarantee we want, and which
RabbitMQ queue type to use. RabbitMQ 4 removed classic mirrored queues; quorum queues are
the replicated option. Celery 5.5+ supports them, but they don't allow global QoS, and
`countdown`/ETA (used by retry backoff) then needs Celery's "native delayed delivery"
topology.

**Decision.**
- **Classic durable queues**, one direct exchange per queue, `default` as fallback.
- **Routing by task name**: `emails.*` → `emails`, `ai.*` → `ai`, everything else →
  `default`. A task's name says where it runs; no per-call `queue=` arguments.
- **At-least-once**: `task_acks_late`, `task_reject_on_worker_lost`,
  `worker_prefetch_multiplier=1`. Tasks must be idempotent and receive IDs, not objects.
- JSON serializer only; results in Redis DB 1 for one day; soft/hard time limits 60/90 s
  by default, overridden per task when needed.

**Alternatives.** *Quorum queues*: replicated and with poison-message `delivery-limit`, but
replication buys nothing on a single node, and delayed delivery adds exchanges and a
dependency on a newer Celery feature. *Per-call routing* (`apply_async(queue=...)`): easy
to forget at one call site. *At-most-once (early ack)*: simpler, but a worker crash
silently drops the task.

**Consequences.** Retry backoff via `countdown` works out of the box. A message can run
twice (crash after side effect, before ack), so every task needs an idempotency guard.
Moving to quorum queues for a multi-node broker (Phase 7) is a config change plus enabling
delayed delivery; task code stays the same.

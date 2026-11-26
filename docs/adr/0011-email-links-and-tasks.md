# 0011 — Email links: single-use tokens created in the worker

**Context.** Email verification and password reset send a link with a secret. We had to
choose the token format, where it is generated, and how the API hands the job to Celery.

**Decision.**
- **Opaque random token, stored as a SHA-256 hash in Redis** with a TTL (24 h verification,
  30 min reset), consumed with `GETDEL`, so it works exactly once. A per-user pointer keeps
  only the newest link valid.
- **The worker generates the token**, not the API. The task message carries only the user
  id, so no secret (and no email address) is stored in RabbitMQ, Flower or task results.
- **Token in the URL fragment** (`/reset-password#token=...`): fragments are never sent to a
  server and never appear in the `Referer` header or access logs.
- **The API enqueues through an `AuthMailer` port** (`CeleryAuthMailer` in production, a
  fake in tests). `.delay()` runs in a thread pool because it does blocking I/O. If the
  broker is down the error is logged and the request still succeeds — the user can resend.
- **Tasks retry only on `IntegrationUnavailableError`** (timeouts, connection errors, SMTP
  4xx/5xx) with exponential backoff and full jitter, at most 5 times. They are idempotent
  in effect: a repeated run sends a fresh link and invalidates the previous one.
- A password reset revokes every refresh-token family and marks the email as verified.

**Alternatives.**
- *Signed JWT in the link*: no storage, but it can't be made single-use or revoked without
  storing its id anyway.
- *Token generated in the API and passed to the task*: simpler, but the secret sits in the
  broker and in Flower.
- *Transactional outbox* instead of enqueueing after commit: no lost emails at all; planned
  in Phase 3 (T2) for domain events, overkill for a resendable email now.

**Consequences.** One Redis round-trip per link; secrets live only in Redis (hashed) and in
the user's inbox. A broker outage during registration loses the first email but nothing
else.

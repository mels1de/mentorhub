# 0008 — Typed settings from flat env vars and one root `.env`

**Context.** The API, Celery workers and Docker Compose services (Postgres, RustFS,
RabbitMQ…) all need configuration. The same code runs on the host (API against the Compose
DB on an offset port) and inside Compose (DB reachable as `db:5432`). Secrets must never
reach logs, and a misconfigured production deploy must not start silently.

**Decision.**
- One `Settings` class (pydantic-settings) in `backend/app/core/config.py` is the only way
  code reads configuration. Precedence: constructor kwargs > environment > `.env` >
  defaults.
- **Flat** variable names (`POSTGRES_HOST`, `POSTGRES_PASSWORD`…), matching what official
  images already read, so one file configures both the DB container and the API.
- **One `.env` at the repository root**, next to `compose.yaml`, found via a path relative
  to `config.py` (not the working directory). `extra="ignore"` because the file also holds
  keys only Compose uses. `.env.example` is the committed template.
- Secrets are `SecretStr`; derived URLs that contain a password are plain properties, not
  computed fields, so they never appear in `repr()` / `model_dump()`.
- With `ENVIRONMENT=production` the app refuses to start on the default or a short
  `SECRET_KEY`, or with `DEBUG=true`.
- Access through a cached `get_settings()` so tests can override it.

**Alternatives.** *Nested models* (`DB__HOST` via `env_nested_delimiter`): tidier in code,
but duplicates every value the official images read under another name. *`os.environ`
reads scattered in code*: no types, no validation, secrets easily logged. *A `.env` per
app*: values drift between `backend/.env` and the Compose file.

**Consequences.** Configuration errors fail at startup with the field name. A typo in a
variable name is silently ignored and the default is used — mitigated by keeping
`.env.example` in sync with `Settings` and by safe local defaults. Tests must isolate
themselves from a developer's `.env` (`_env_file=None`).

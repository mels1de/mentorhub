# 0006 — Python 3.14 + uv; Vue 3 + TypeScript + TanStack Query

**Decision.** Backend on Python 3.14 (stdlib `uuid.uuid7`, PEP 695 generics) managed by
`uv` with a committed lockfile; Ruff for lint+format, mypy strict. Frontend on Vue 3 with
TypeScript, Vite, Pinia for client state and TanStack Query for server state (cache,
pagination, polling, retries); API types generated from the backend's OpenAPI schema.

**Alternatives.** Poetry/pip-tools (slower, more tools); plain JavaScript (no compile-time
contract with the API); Pinia for server state (re-implementing caching by hand).

**Consequences.** Fast reproducible installs locally, in Docker and in CI from the same
lockfile. Backend schema changes surface as frontend type errors.

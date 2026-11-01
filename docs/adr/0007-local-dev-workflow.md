# 0007 — Local dev: backend + services in Docker, frontend on the host

**Context.** The repo is a monorepo with two apps, `backend/` and `frontend/`. The thesis
requires the whole system to run in containers, but day-to-day frontend work needs instant
hot module replacement, and bind-mounted `node_modules` on macOS Docker is slow. The
development machine also runs unrelated projects, so the stack must not collide with them.

**Decision.**
- **Daily development:** `make up` starts the backend (FastAPI with hot reload via a bind
  mount), Celery worker/beat, the one-shot `migrate` job and all services (Postgres, Redis,
  RabbitMQ, RustFS, Mailpit) in Docker Compose. The frontend runs on the host with
  `npm run dev`; the Vite dev server proxies `/api`, `/health`, `/ws` to the backend's
  published port.
- **Full containerised run (demo, thesis, CI smoke test):** the Compose profile `web` adds
  the production frontend image (static build served by nginx, same proxy rules), so
  `make up-full` runs everything in containers.
- The frontend has **no dev container**: one fewer image to maintain; Node 24 on the host is
  pinned by `.node-version`.
- **Isolation:** Compose project name `mentorhub` (every container, network and volume is
  prefixed), host ports bound to `127.0.0.1` and offset from defaults (e.g. Postgres
  `15432`), so it coexists with a locally installed Postgres or other stacks.

**Alternatives.**
- Everything in Docker, including a Vite dev container: one command, identical environment,
  but slower HMR and file watching on macOS, `node_modules` volume tricks.
- Everything on the host: fastest feedback, but every developer installs and runs Postgres,
  Redis, RabbitMQ… locally and versions drift from production.

**Consequences.** Fast frontend feedback, reproducible backend environment, and the full
containerised setup required by the thesis is still one command away. Developers need
Node 24 on the host. The host-run frontend and the nginx image must keep the same proxy
paths — covered by running the `web` profile in CI.

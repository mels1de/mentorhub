# Technology decisions & verified facts

Versions below were checked against package registries on **2026-10-31** while
prototyping the stack (a throwaway prototype built and passed lint/type/tests with these).
Use them as the starting point; `uv add` / `npm install` will pick the latest compatible.

## Backend

| Choice | Version seen | Why / notes |
|---|---|---|
| Python | **3.14** | stdlib `uuid.uuid7()` (time-ordered PKs), PEP 695 generics `class Page[T]`. All deps below install fine on 3.14. Pin in `backend/.python-version`. |
| uv | 0.11 (0.13.6 installed 2026-10-31) | Project & lockfile manager. `uv add`, `uv sync --locked`, `uv run`. Lockfile committed. |
| FastAPI | 0.162 | |
| Pydantic / pydantic-settings | 2.14 / 2.16 | `SecretStr` for secrets; `NoDecode` + validator to accept comma-separated `CORS_ORIGINS`. |
| SQLAlchemy | **2.1** (async) + asyncpg 0.32 | `async_sessionmaker(expire_on_commit=False)`; naming convention on `MetaData` for Alembic. |
| Alembic | 1.20 | Async `env.py`; URL from Settings, not alembic.ini; ruff post-write hook. |
| Redis client | redis-py 8.1 (`redis.asyncio`) | |
| Celery | 5.6 | RabbitMQ broker, Redis result backend; `celery-types` for mypy. |
| structlog | 26.x | JSON in containers, console locally; route stdlib/uvicorn logs through it. |
| Metrics | prometheus-fastapi-instrumentator 8.1 | `/metrics`, exclude `/health` and `/metrics` from instrumentation. |
| Passwords | `pwdlib[argon2]` | passlib is unmaintained; FastAPI docs moved to pwdlib. |
| JWT | PyJWT | |
| Dev | pytest 9, pytest-asyncio 1.4, pytest-cov, httpx, ruff 0.17, mypy (strict) | |

## Frontend

| Choice | Version seen | Notes |
|---|---|---|
| Scaffold | `npm create vue@latest` (create-vue 3.24) with `--ts --router --pinia --vitest --eslint --prettier` | Generates oxlint + ESLint flat config + Prettier. |
| Node / npm | **Node 24, npm 11** (24.22.2 / 11.19.1 installed) | Pinned in root `.node-version`, used by fnm locally and `actions/setup-node` in CI. |
| Vue / Vite / Router / Pinia | 3.5 / **8.x** / 5.x / 4.x | TypeScript ~6.0. |
| TanStack Query (`@tanstack/vue-query`) | 5.x | Server state, pagination (`keepPreviousData`), polling (`refetchInterval`). |
| Tailwind CSS | **4.x** via `@tailwindcss/vite` | CSS-first config (`@import 'tailwindcss'`, `@theme`), class-based dark mode via `@custom-variant dark`. |
| axios | 1.x | One shared instance, relative `baseURL` `/api/v1`. |
| Forms | VeeValidate + Zod | |

## Infrastructure

| Choice | Notes |
|---|---|
| PostgreSQL **17** + **pgvector** + **PostGIS** | No official image has both extensions → tiny custom image: `FROM pgvector/pgvector:pg17` + `apt-get install postgresql-17-postgis-3`. (PG18 changed the data dir layout for volumes; 17 avoids that gotcha.) |
| Redis **8** (`redis:8-alpine`) | `--appendonly yes`. |
| RabbitMQ **4** (`rabbitmq:4-management-alpine`) | UI on 15672; `rabbitmq-diagnostics -q ping` healthcheck; Prometheus plugin on 15692. |
| S3 locally: **RustFS** (`rustfs/rustfs`) | **MinIO community edition is discontinued** — Docker Hub images removed, repo archived (2026). RustFS: env `RUSTFS_ACCESS_KEY`, `RUSTFS_SECRET_KEY`, `RUSTFS_ADDRESS=:9000`, `RUSTFS_CONSOLE_ADDRESS=:9001`, `RUSTFS_CONSOLE_ENABLE=true`, data in `/data`, runs as UID 10001. Create the bucket with a one-shot `amazon/aws-cli` container. Prod: AWS S3 or Cloudflare R2. |
| Email locally: **Mailpit** (`axllent/mailpit`) | SMTP 1025, UI 8025. |
| Observability | Prometheus + Grafana (provisioned datasource + dashboard JSON) + alert rules; Flower for Celery; Sentry later. |
| Local LLM | Ollama (optional Compose profile). |
| Container runtime on Mac | OrbStack or Docker Desktop. |
| Orchestration | Kubernetes via k3d locally, Kustomize overlays (Phase 7). |

## Target developer experience (Phase 0 builds this)

- **Monorepo:** `backend/` and `frontend/` side by side, root holds `compose.yaml`,
  `Makefile`, `docs/`, CI. **Dev workflow ([ADR-0007](adr/0007-local-dev-workflow.md)):**
  backend + all services in Docker (`make up`), frontend on the host (`npm run dev`, Node 24
  from `.node-version`); profile `web` adds the nginx frontend image for a fully
  containerised run (`make up-full`, demo/thesis).
- `compose.yaml` with `name: mentorhub` and **profiles**: core stack by default; `web`
  (prod frontend image); `observability` (Prometheus, Grafana, Flower); `ai` (Ollama).
- **Host ports:** bound to `127.0.0.1` and **offset from defaults** so the stack coexists
  with other local projects (a host Postgres on 5432, dev servers on 3000):
  Postgres `15432`, Redis `16379`, RabbitMQ `15673` (UI) / AMQP not published, API `8000`,
  Vite `5173`, Mailpit UI `8025`, RustFS `19000`/`19001`. Inside the Compose network
  services use their normal ports. Final list confirmed in Session 0.5.
- **Isolation rule:** only project-scoped Docker commands (`make`, `docker compose ...`
  in this repo); never global `docker ... prune`.
- Shared backend service definition via YAML anchor for `backend`, `worker`, `beat`,
  one-shot `migrate`; `backend` waits for `migrate: service_completed_successfully` and
  healthy db/redis/rabbitmq. Inside Compose override hosts (`POSTGRES_HOST=db`, etc.) so
  the same `.env` also works when running the API on the host.
- Backend Dockerfile: multi-stage with uv (`deps` → `dev` with hot reload | `prod`
  non-root + HEALTHCHECK). Put the venv at `/opt/venv` (`UV_PROJECT_ENVIRONMENT`) so the
  dev bind mount `./backend:/app` doesn't hide it.
- Frontend Dockerfile: `deps` → `build` → `prod` on `nginxinc/nginx-unprivileged` with SPA
  fallback and `/api`, `/health`, `/ws` proxied to the backend (no dev target — dev runs on
  the host). In dev the Vite proxy does the same against `http://localhost:8000` (no CORS
  pain); keep both proxy configs in sync.
- Celery worker in dev auto-restarts on code change via `watchfiles` (comes with
  `uvicorn[standard]`).
- `Makefile` shortcuts: `up`, `up-full`, `up-obs`, `down`, `fe` (`npm run dev`), `logs`, `migrate`, `revision m=...`,
  `test`, `lint`, `fmt`, `psql`, `gen-api`.
- Health: `/health/live` (process only) and `/health/ready` (DB + Redis, 503 if down).
- Ignore files: `.gitignore` (secrets, venvs, caches, `.personal/`, `personal.mdc`),
  `.dockerignore` per service, `.cursorignore` (secrets, deps, lockfiles), `.editorconfig`.
- pre-commit: pre-commit-hooks, ruff, gitleaks, frontend lint.
- GitHub Actions: backend (ruff, mypy, compose up db+redis, **alembic upgrade → downgrade
  → upgrade**, pytest with integration tests), frontend (lint, format, type-check, Vitest,
  build), docker (build `prod` targets → GHCR on push to `main`), Dependabot (uv, npm,
  actions, docker). Lint workflows with `actionlint`.

## Gotchas already hit (save the time)

- **npm 10 crashed** on install (`Cannot read properties of null (reading 'edgesOut')`);
  **npm 11 works**. Use Node 24 (ships npm 11). npm 11 also blocks install scripts by
  default — that's fine for this stack.
- create-vue's `vitest.config.ts` does `mergeConfig(viteConfig, ...)`. If you turn
  `vite.config.ts` into a function (to read env like `VITE_PROXY_TARGET`), vitest
  config must call it: `defineConfig((env) => mergeConfig(viteConfig(env), {...}))`.
- `openapi-typescript` (for `npm run gen:api`) had a peer-dependency conflict with
  TypeScript 6 → run it via `npx -y openapi-typescript ...` instead of installing.
- Ruff's **`TC` (flake8-type-checking) rules break FastAPI/Pydantic**: they move imports
  needed at runtime for dependency injection into `TYPE_CHECKING` blocks. Don't enable TC.
- `httpx.ASGITransport` does **not** run the app lifespan → in API tests don't rely on
  resources created in lifespan, or override the dependency.
- Use a **pure ASGI middleware** for request IDs/access logs (not `BaseHTTPMiddleware`),
  it's faster and safe with streaming/WebSockets.
- Readiness checks: run them concurrently with a per-check timeout (`asyncio.wait_for`),
  otherwise one hanging dependency hangs the probe.
- In Celery, `task_acks_late=True` + `worker_prefetch_multiplier=1` +
  `task_reject_on_worker_lost=True` → at-least-once delivery ⇒ tasks must be idempotent.
- Desktop/Documents on this Mac may sync to iCloud — keep the repo in `~/Projects/`
  (not synced) or `node_modules` / `.venv` will be uploaded endlessly.

## Third-party notes

- **reCAPTCHA v3** keys are now managed in a Google Cloud project; verify score + expected
  `action`. Keep it behind a `CaptchaVerifier` port (Cloudflare Turnstile = drop-in).
- **Google Maps**: Places Autocomplete on the frontend, Geocoding on the backend; needs a
  billing-enabled Google Cloud project — restrict keys by HTTP referrer / API.
- **DocuSign**: free developer sandbox; webhooks via Connect with HMAC verification.
- **LLMs**: provider behind an `LLMClient` port. Anthropic models e.g.
  `claude-haiku-5-5` (cheap), `claude-sonnet-5-5`; embeddings from OpenAI
  (`text-embedding-3-small`, 1536 dims) or local Ollama (`nomic-embed-text`, 768 dims).
  Anthropic has no embeddings API.

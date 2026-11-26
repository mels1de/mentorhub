# Development guide

Day-to-day workflow ([ADR-0007](adr/0007-local-dev-workflow.md)): the backend and every
service run in Docker Compose, the frontend runs on the host for instant hot reload.
All commands run from the repository root; `make help` lists them.

## First setup

```bash
cp .env.example .env          # optional: defaults already work locally
uvx pre-commit install        # git hooks: ruff, gitleaks, frontend lint
cd backend && uv sync && cd ..
cd frontend && npm install && cd ..
```

## Run

| Command | What it does |
|---|---|
| `make up` | Build and start backend, worker, beat, the one-shot `migrate` job and all services |
| `make fe-dev` | Vite dev server on <http://localhost:5173>, proxies `/api`, `/health`, `/ws` to the API |
| `make up-full` | Everything in containers, incl. the nginx frontend on <http://localhost:18080> |
| `make ps` | Status; `migrate` should be `Exited (0)`, the rest `Up` / `healthy` |
| `make down` | Stop everything, **keep** data volumes |

Never run `docker compose down -v` unless you want to delete all local data.

Code changes reload automatically: uvicorn `--reload` for the API, `watchfiles` for the
Celery worker, Vite HMR for the frontend. Beat needs `make restart s=beat` after schedule
changes.

## Ports (host, bound to 127.0.0.1)

| Service | Address |
|---|---|
| API / Swagger UI | <http://localhost:18000> / <http://localhost:18000/docs> |
| Frontend dev / nginx | <http://localhost:5173> / <http://localhost:18080> |
| PostgreSQL | `localhost:15432` (user, password, db: `mentorhub`) |
| Redis | `localhost:16379` |
| RabbitMQ AMQP / UI | `localhost:15672` / <http://localhost:15673> |
| RustFS S3 / console | <http://localhost:19000> / <http://localhost:19001> |
| Mailpit UI / SMTP | <http://localhost:8025> / `localhost:11025` |

Host ports are offset from the defaults so the stack coexists with other local projects;
inside the Compose network services use their normal ports (`db:5432`, `redis:6379`...).

## Logs

```bash
make logs                 # all services
make logs s=backend       # one service (backend, worker, beat, migrate, db, ...)
```

Every request gets an `X-Request-ID` (echoed in the response and in Problem Details
bodies); search the logs for it to follow one request. Successful `/health/*` and
`/metrics` requests are not access-logged. `LOG_FORMAT=json` switches to JSON lines.

## Database

```bash
docker compose exec db psql -U mentorhub -d mentorhub   # psql inside the container
```

Useful psql commands: `\dt` tables, `\d table` structure, `\dx` extensions, `\q` quit.
Any GUI client works too: `localhost:15432`.

## Migrations

```bash
make migrate                          # alembic upgrade head
make revision m="add users table"     # autogenerate from models, then REVIEW the file
docker compose run --rm migrate alembic downgrade -1   # roll back one step
docker compose run --rm migrate alembic current        # current revision
docker compose run --rm migrate alembic history        # all revisions
```

Autogenerate is a draft: check every generated migration (renames show up as drop + add,
server defaults and constraints may need manual edits). CI runs upgrade → downgrade →
upgrade, so every migration must be reversible.

## Tests and linters

| Command | What |
|---|---|
| `make test` | Backend tests; integration tests need `make up` (skipped locally if services are down, fail in CI) |
| `make test-unit` | Backend tests without real services |
| `make lint` / `make fmt` | Ruff + mypy strict / auto-fix |
| `make fe-test` | Vitest |
| `make fe-lint` | oxlint + ESLint (auto-fix) + `vue-tsc` |
| `uvx pre-commit run --all-files` | All git hooks on the whole repo |

Integration tests never touch dev data: they create and migrate a separate `mentorhub_test`
database on the first run, run each test inside a transaction that is rolled back, and use
Redis DB 15, flushed after every test.

## Accounts

Register mentees and mentors through the API or the UI. Admins only from the CLI:

```bash
make create-admin email=admin@example.com   # prompts for the password
```

## API types for the frontend

After changing the API, with the backend running:

```bash
make gen-api      # writes frontend/src/api/schema.d.ts from /openapi.json
```

## Celery

```bash
docker compose exec backend python -c \
  "from app.worker.system import ping; print(ping.delay().get(timeout=10))"   # → pong
```

Queues and messages: RabbitMQ UI on <http://localhost:15673> (`mentorhub` / `mentorhub`).

## CI

`.github/workflows/ci.yml` runs on every PR and on `main`: backend (ruff, mypy, migrations
round-trip, pytest with Postgres, Redis, RabbitMQ), frontend (lint, format, type-check, Vitest,
build), actionlint, and builds both prod images (pushed to GHCR only from `main`).

## Dependency updates

Dependabot runs weekly. Minor and patch updates arrive as one grouped PR per ecosystem;
every major update gets its own PR, so one breaking release cannot block the safe ones.

- Merge a grouped PR when CI is green. CI does not start RustFS or Mailpit, so for the
  `compose` group also run `make up` and check `/health/ready` locally.
- A major PR needs its changelog read and, if needed, code changes on the same branch.
- Node stays on the major in `.node-version` (24 LTS) on the host, in CI and in the image;
  majors of `node`, `@types/node` and `@tsconfig/node*` are ignored until we move all three.
- `typescript` majors are ignored until `typescript-eslint` supports them.

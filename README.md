# MentorHub

[![CI](https://github.com/mels1de/mentorhub/actions/workflows/ci.yml/badge.svg)](https://github.com/mels1de/mentorhub/actions/workflows/ci.yml)

A mentorship platform: mentees find mentors, book sessions in their available slots, get
reminders and notifications, leave reviews and use AI to find the right mentor.
Bachelor's thesis project (BSc in AI Development, Vistula University).

> Status: foundation (Phase 0) — infrastructure, health checks, CI. Features follow the
> [roadmap](docs/ROADMAP.md).

## Stack

| Layer | Technology |
|---|---|
| API | Python 3.14, FastAPI, Pydantic, SQLAlchemy 2 (async), Alembic |
| Data | PostgreSQL 17 + pgvector + PostGIS, Redis |
| Background jobs | Celery + RabbitMQ (queues `default` · `emails` · `ai`), Celery beat |
| Storage / mail | S3-compatible (RustFS locally), SMTP (Mailpit locally) |
| Frontend | Vue 3 + TypeScript, Vite, Pinia, TanStack Query, Tailwind CSS 4 |
| Tooling | uv, Ruff, mypy (strict), pytest, Vitest, ESLint/oxlint, Prettier |
| Delivery | Docker multi-stage images, Docker Compose, GitHub Actions → GHCR |

## Quick start

Requirements: Docker Desktop, [uv](https://docs.astral.sh/uv/), Node 24 (`.node-version`).

```bash
make up                              # backend, worker, beat, migrations, all services
cd frontend && npm install && cd ..  # first time only
make fe-dev                          # frontend dev server
```

Open <http://localhost:5173>. API docs: <http://localhost:18000/docs>.
Everything in containers (demo): `make up-full` → <http://localhost:18080>.

Full guide — ports, logs, database access, migrations, tests: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [architecture decision records](docs/adr/)
- [Tech decisions and versions](docs/TECH_DECISIONS.md)
- [Error codes](docs/errors.md)
- [Roadmap](docs/ROADMAP.md)

## License

[MIT](LICENSE)

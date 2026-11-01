# Project brief

## The thesis

Bachelor's thesis, BSc in AI Development (AI / ML Engineering), Vistula University, Warsaw.
Approved topic (original wording, Polish):

> Projekt nosi nazwę **MentorHub API**. Projekt będzie składał się z: backendu napisanego
> w języku Python z wykorzystaniem frameworka FastAPI, lokalnej bazy danych,
> konteneryzacji aplikacji przy użyciu Dockera, frontendu stworzonego w technologii
> Vue.js. Celem pracy będzie zaprojektowanie i implementacja kompletnego systemu API,
> integracja warstwy frontendowej z backendem oraz zapewnienie poprawnego działania
> aplikacji w środowisku kontenerowym.

So the **minimum the committee expects**: a complete, well-designed API + database +
Docker + a Vue frontend integrated with it, all running in containers. Everything else
below is added value — valuable, but never at the expense of that core.

## The product

A mentoring platform. **Mentees** find mentors by skills, location and price, book
sessions in the mentor's available slots, sign an agreement, get reminders and real-time
notifications, leave reviews and use AI to find the right mentor and plan their learning.
**Mentors** manage profile, availability, booking requests and see their rating.
**Admins** moderate, see leads, send announcements.

## Feature list (everything Artemii wants in the project)

Core
- Registration and login forms with validation; roles mentee / mentor / admin (RBAC)
- Mentor profiles, skills catalog, availability schedule
- Catalog search with filters, sorting and **pagination** (no huge payloads, no lag)
- Booking flow with statuses; reviews and ratings
- Data persisted in PostgreSQL with versioned migrations

Security
- JWT access + refresh tokens, logout / revocation
- **2FA with a code sent to the user's email**
- **Auto-logout on inactivity** (track mouse / keyboard / scroll; warning before logout)
- **reCAPTCHA** against bots on public forms
- Rate limiting

Performance & async
- **Redis** caching (+ token storage, rate-limit counters)
- **Background tasks and queues: Celery + RabbitMQ** (emails, reminders, AI jobs)
- **Polling** for some operations (e.g. status of long-running jobs/bookings), WebSockets
  for real-time where it matters

Notifications
- **Notification system per role and per entity** (new booking → mentor, confirmed →
  mentee, new review → mentor, reminders → both, etc.), stored + delivered in real time

Third-party integrations
- **Google Maps — map-based mentor search**: mentor locations in PostGIS
  (`geography(Point, 4326)`, GiST index); a search box with **Places Autocomplete** (type a
  city or address → the map moves there → nearby mentors load); **"search this area"** for
  the visible map region (bounding box); **"within X km"** filter and **sort by distance**;
  **"near me"** via browser geolocation; **marker clustering**, mentor card on marker
  click; combined with the other catalog filters (skills, price, rating) and pagination.
  Mentors' exact addresses are never exposed publicly. Places Autocomplete is also used
  for address input in the mentor profile.
- **DocuSign**: e-signature of the mentorship agreement
- **S3** object storage for files (avatars, signed documents, PDFs)
- Email delivery (SMTP provider)

Marketing
- **Lead capture forms** (no account needed), stored for follow-up, export

AI
- **LLM integration** (OpenAI / Anthropic / local) for quick answers and recommendations
  to users: assistant chat, mentor recommendations, generated learning plans
- **RAG** — Artemii wants to learn what it is and use it properly (semantic mentor
  matching, Q&A over a knowledge base)
- **AI automation** — background pipelines (summaries, moderation, classification)

Engineering & operations
- **Metrics / traffic monitoring**: Prometheus + Grafana (+ alerts)
- **CI/CD with GitHub Actions**
- **Kubernetes** orchestration (autoscaling, rolling updates)
- Docker + Docker Compose done right, correct `.gitignore` / `.dockerignore`
- **Tests for the main functionality**
- **Git branching**: a branch per feature/upgrade, merged into `main` via PRs
- Maintainable, scalable architecture following current best practices

## About Artemii (context for how to help)

- 20, final-year student; full-time remote full-stack developer (~1 year) at an
  Australian company: FastAPI, Django REST, PostgreSQL, Vue.js, Docker, GitHub Actions,
  Azure. Built a notification system, a large third-party integration (OAuth2, webhooks,
  retries), dark mode, async REST APIs with versioning, query optimisation, pytest.
- Schedule: work 06:00–14:00 (Warsaw), then university. Limited evening/weekend time.
- At work most code is AI-generated (company policy). Here too Claude writes the code,
  but the point of the project is that **he makes the design decisions and deeply
  understands why the code is written the way it is** — see working mode in personal rules.
- New for him / wants to learn: Celery + RabbitMQ in depth, observability, Kubernetes,
  LLM integration, RAG, AI automation, and using Cursor + Claude Code well.
- IDE: Cursor (moving from PyCharm/WebStorm). Machine: MacBook Pro, Apple Silicon.
- GitHub: `mels1de`. The repo will be **public** as a portfolio piece.

## Goals and success criteria

1. **Thesis defended with a top grade.** He can explain every design decision, its
   alternatives and trade-offs; live demo works from `docker compose up`.
2. **Portfolio for the next job** (mid-level full-stack/backend with AI integration):
   clean repo, README with diagrams, CI badges, live demo if possible.
3. **Real skill growth**: by the end he can explain any part of the system, justify
   every architectural choice against alternatives, debug it, extend it confidently, and
   explain RAG end-to-end.

## Constraints

- **Original code only.** Nothing copied from his employer's codebase.
- Defense date: see personal rules (`Thesis defense date`). Prioritise roadmap tiers
  (T1 must, T2 should, T3 showcase) accordingly.
- Budget: student. Prefer free tiers, local alternatives (Ollama, Mailpit, RustFS) in dev,
  cheap models by default, hard caps on paid API usage.

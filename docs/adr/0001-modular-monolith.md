# 0001 — Modular monolith with vertical-slice modules

**Context.** One developer, limited time, a thesis that must demonstrate clean
architecture and scalability. Features: auth, catalog, bookings, notifications, AI.

**Decision.** A single FastAPI service organised by feature (`app/modules/<feature>`), each
module layered internally (router → service → repository). Modules talk only via services.
Horizontal scaling by running more replicas of the same stateless API.

**Alternatives.** *Microservices*: independent scaling and deploys, but network calls,
distributed transactions, N pipelines and much more ops work for no real benefit at this
size. *Layer-first layout* (`routers/`, `services/`, `models/` at top level): simple at
first, but a feature is smeared across the tree and boundaries erode.

**Consequences.** Simple deploy and local dev; transactions stay local. Boundaries must
be enforced by convention and review (could add `import-linter` later). A module with
very different load (e.g. AI) can be extracted later behind the same service interface.

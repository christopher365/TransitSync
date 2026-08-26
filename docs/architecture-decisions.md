# TransitSync — Architecture Decisions

Trade-off notes for the major decisions baked into the backend scaffold, per the
project's working agreement that architectural choices get a comparative note
rather than a silent pick. See `CLAUDE.md` for the full constraints these are
weighed against (solo dev, few weeks, $0 budget, eventual consistency is fine).

## Data source: MBTA V3 API (pivoted from Metra GTFS-RT + OSU CABS)

**Chosen:** MBTA's V3 API (`https://api-v3.mbta.com`), a free JSON:API-style REST
API that includes a `/vehicles` endpoint for live vehicle positions, plus static
reference data (`/routes`, `/stops`).

**Alternatives considered:**
- *Metra GTFS-Realtime (protobuf feed):* Chicago commuter rail's official
  real-time feed. Rejected for v1 — parsing raw GTFS-RT protobuf adds a decoding
  step and a stricter, less forgiving schema than a JSON REST API, for no gain
  given the project's actual goal (a working real-time sync demo, not
  GTFS-RT-format expertise specifically).
- *OSU CABS:* Ohio State's campus bus data. Rejected for v1 — no stable public
  real-time API was confirmed available; blocking the ingestion layer on an
  uncertain data source risked the "few weeks to v1" timeline.

**Why MBTA wins given the constraints:** it's free, well-documented, includes
both static and real-time data behind one consistent API, and needs no protobuf
tooling — lowest integration risk for a solo dev on a tight timeline. Multiple
agencies can be added later behind the same repository interfaces if time
allows (see Repository Pattern below).

## Web framework: FastAPI

**Chosen:** FastAPI, for both the REST endpoints and the WebSocket layer.

**Alternatives considered:** Flask (+ Flask-SocketIO) and Django (+ Channels).
Rejected — FastAPI has first-class native WebSocket support (no extra
extension), built-in async support for concurrent polling + broadcast, and
Pydantic-based request/response validation "for free," which directly serves
the working agreement's input-validation requirement.

## Database & ORM: PostgreSQL + SQLAlchemy 2.0 + Alembic

**Chosen:** PostgreSQL (via a free tier, e.g. Neon/Supabase), SQLAlchemy 2.0's
typed `Mapped[...]` style, Alembic for migrations.

**Alternatives considered:**
- *Raw SQL / a query builder:* faster to write initially, but the schema will
  evolve across the ingestion and API layers still to come — hand-written
  migrations are more error-prone than Alembic's autogenerate-from-model diffing.
- *SQLite for v1:* rejected for anything beyond tests — the concurrency and
  volume targets (1,000+ concurrent clients, 10,000+ daily coordinate writes)
  need a real server-side database, and Postgres has a genuine free tier.
- *MongoDB:* rejected — the data (stops, routes, vehicle positions) is
  naturally relational (routes ↔ stops is many-to-many), and eventual
  consistency doesn't require a document store.

## Persistence access: Repository pattern (interface + implementation split)

**Chosen:** an abstract `*RepositoryInterface` per aggregate (e.g.
`StopRepositoryInterface`) with a SQLAlchemy-backed implementation
(`SqlAlchemyStopRepository`), per the Dependency Inversion Principle.

**Alternatives considered:** calling the SQLAlchemy `Session` directly from
route handlers / ingestion code. Rejected — it would couple business logic to
the ORM, making it harder to unit test (see `tests/conftest.py`'s in-memory
SQLite fixture, which only works because tests depend on the interface, not
the database) and harder to swap a data source later.

## Ingestion pattern: poll → ingest → broadcast (no message queue)

**Chosen:** a scheduled poller hits the MBTA API, upserts/logs into Postgres,
then broadcasts to connected WebSocket clients directly — no Kafka or other
event-streaming platform in between.

**Why:** explicitly required by the project constraints — a few seconds of
position staleness is acceptable, so the added operational complexity and cost
of a streaming platform isn't justified. This is the simplest design that
meets the sub-500ms client-sync target, since polling interval and broadcast
are both in-process.

## Testing: pytest + in-memory SQLite, not a live Postgres in CI

**Chosen:** repository/unit tests run against a fresh in-memory SQLite database
per test (`tests/conftest.py`), not a real Postgres instance.

**Alternatives considered:** a containerized Postgres for tests (e.g. via
`testcontainers`). Rejected for now — adds CI complexity and runtime for
marginal benefit, since the Repository pattern means the code under test
doesn't know which database it's talking to. Worth revisiting once
Postgres-specific features (e.g. `ilike`, JSON columns) are used in ways SQLite
can't emulate.

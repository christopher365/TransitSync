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

## Bridging sync ingestion into the async WebSocket server: asyncio.to_thread

**Chosen:** the ingestion pipeline (HTTP call + DB write) stays fully
synchronous, per the earlier ingestion-pattern decision. `VehiclePoller`
(the background polling loop) is async — FastAPI's WebSocket connections
require an async event loop — and calls the sync poll function via
`await asyncio.to_thread(poll_fn)` on each cycle.

**Alternatives considered:** rewriting the MBTA client and repository layer
as async (`httpx.AsyncClient`, SQLAlchemy's `AsyncSession`). Rejected for
v1 — it would mean two parallel implementations of the same repository
pattern (sync for tests/scripts, async for the live server) for a workload
that polls once every few seconds, not thousands of times a second. The
event-loop-blocking risk `asyncio.to_thread` exists to solve only matters
because the *same* process also serves WebSocket clients; isolating the
blocking work onto a worker thread solves that without an async rewrite.

## Application factory pattern: `create_app()` instead of a module-level app

**Chosen:** `app/main.py` exposes `create_app(session_factory=..., poll_fn=...)`,
which builds and returns a fresh `FastAPI` instance; a plain `app = create_app()`
at module level is what Uvicorn actually runs.

**Alternatives considered:** building `app`, the DB engine, and the poller
directly at module scope (as most FastAPI tutorials show). Rejected —
tests would then have no way to swap in an in-memory SQLite database or a
network-free poll function; they'd either need a real Postgres and a real
MBTA connection just to test that a WebSocket sends a JSON message, or
they'd have to monkeypatch module globals, which gets fragile fast. The
factory makes "what this app depends on" explicit and swappable at the one
place it's constructed.

## Poll interval: 5 seconds

**Chosen:** the poller re-fetches MBTA vehicle positions every 5 seconds.

**Why:** MBTA's vehicles typically update server-side every ~10–15 seconds
regardless of how often we ask, so polling much faster wastes requests
without fresher data; polling much slower would visibly lag behind actual
vehicle movement on the dashboard. 5 seconds is comfortably inside MBTA's
public rate limits and leaves headroom to tighten later if profiling shows
it's worth it — an easy constant to change, not an architectural commitment.

## Docker: multi-stage build, non-root user

**Chosen:** `backend/Dockerfile` builds dependencies into a venv in a
`builder` stage, then copies just that venv plus the app code into a slim
final image, running as a created non-root user.

**Alternatives considered:** a single-stage `pip install` directly into the
final image. Since every dependency here ships a pre-built binary wheel
(notably `psycopg-binary`, chosen specifically to avoid needing a C compiler
in the image), the size difference is modest — but multi-stage still keeps
pip's cache and installer metadata out of the shipped image, and it's the
default professional pattern worth using even when the win is small, since
it costs nothing extra to maintain here. Running as root inside the
container was rejected outright — if the app process were ever compromised,
running as an unprivileged user limits what it could do to the container.

## Schema bootstrap: `Base.metadata.create_all()`, not an Alembic migration yet

**Chosen:** the FastAPI app calls `Base.metadata.create_all(bind=engine)` on
startup (see `app/main.py`'s `lifespan`) to create any missing tables.

**Why not Alembic**, despite it being the chosen migration tool (see above):
generating a correct *first* migration with `alembic revision --autogenerate`
needs a live database connection to diff against, and no Postgres instance
exists yet at this point in the project (Docker itself was only just being
installed). Hand-writing that first migration blind, with no database to
test it against, risks it being subtly wrong in ways `create_all` (which
just reflects the SQLAlchemy models directly) cannot be. Once a real
Postgres instance exists (local via `docker compose up`, or a free-tier
Neon/Supabase instance), the next step is: run `alembic init`, `alembic
revision --autogenerate -m "initial schema"` against it, verify the
generated migration, then swap this `create_all()` call for `alembic upgrade
head`. Tracked as a follow-up, not forgotten scope.

## CI/CD scope for v1: test + Docker build validation, not live deployment

**Chosen:** `.github/workflows/ci.yml` runs the pytest suite and validates
that `docker build` succeeds, on every push/PR. It does not deploy anywhere.

**Why:** the $0 budget constraint means there's no paid VM to deploy to, and
no free hosting target (e.g. Fly.io, Render) has been chosen yet — there
isn't even a GitHub remote configured for this repo yet. Building "deploy to
nowhere" would be speculative work with no way to verify it actually works.
Once a free hosting target is chosen, the natural next addition is a job
that builds and pushes the image to GitHub Container Registry (free, and
authenticates via the repo's built-in `GITHUB_TOKEN` — no extra secrets
needed) so that target can pull it.

## Testing: pytest + in-memory SQLite, not a live Postgres in CI

**Chosen:** repository/unit tests run against a fresh in-memory SQLite database
per test (`tests/conftest.py`), not a real Postgres instance.

**Alternatives considered:** a containerized Postgres for tests (e.g. via
`testcontainers`). Rejected for now — adds CI complexity and runtime for
marginal benefit, since the Repository pattern means the code under test
doesn't know which database it's talking to. Worth revisiting once
Postgres-specific features (e.g. `ilike`, JSON columns) are used in ways SQLite
can't emulate.

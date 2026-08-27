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

## Stop search + arrival predictions: REST, not another WebSocket channel

**Context:** live-mapping every vehicle system-wide (the original feature)
turned out not to answer a real question a person actually has — confirmed
by testing the clustered/color-coded map live and getting direct feedback
that it still had no *purpose*. "When's the next bus at my stop" is that
real question, and MBTA exposes it via two more V3 endpoints: `/stops`
(static reference data) and `/predictions` (live, per-stop).

**Chosen:** two plain REST endpoints — `GET /api/stops?q=` (search, backed
by our own `stops` table) and `GET /api/stops/{id}/predictions` (proxies
live to MBTA, not persisted) — rather than extending the WebSocket.

**Why REST here, when vehicles use a WebSocket:** the two data shapes are
fundamentally different in access pattern. Vehicle positions are "everyone
connected wants every update, continuously" — a natural fit for a
server-push broadcast. Predictions are "one person wants this one stop's
data, right now, on demand" — a natural fit for request/response; a
WebSocket would mean the server tracks per-client subscriptions to specific
stops for no real benefit over a simple GET the client can re-poll.

**Stops are synced once at startup, not continuously polled:** unlike
vehicle positions, stops essentially never change during a demo session.
`StopSyncService` runs once when the app starts (alongside the
`create_all()` schema bootstrap) rather than on `VehiclePoller`'s repeating
cycle. `upsert()` makes re-running it safe on every restart.

**Scoped to subway/light rail stops only** (MBTA route_type `0,1`): the
full system has thousands of bus stops; syncing all of them needs pagination
handling for comparatively little demo value. Trivial to widen later.

**Predictions are never written to Postgres**: they're only meaningful for
the next several minutes and change on every poll — persisting them would
mean building staleness/expiry logic for data with no lasting value. Fetched
live from MBTA on each request instead.

**CORS was added at this point, not earlier:** the WebSocket handshake
isn't subject to the browser's CORS checks, so nothing needed it while the
WebSocket was the only thing the frontend talked to. Plain HTTP endpoints
are subject to CORS, so `search_stops`/`get_stop_predictions` needed
`CORSMiddleware` added to be reachable from the frontend's origin at all.
Configured to allow any origin — there's no auth or cookies involved, and
this only ever serves public transit data, so the usual "wildcard CORS is
risky" concern doesn't really apply here.

## Production hardening: health check, structured logging, rate limiting

**Context:** added deliberately as a "does this person think about running
software in production, not just writing it" pass, prompted directly by a
request to make the app read more like an industry product.

**Health check (`GET /health`):** checks real DB connectivity (a lightweight
`SELECT 1`), not just "is the process alive" — a service that's running but
can't reach its database is still broken for a load balancer's purposes.
Returns 503 (not 200) when the DB is unreachable, so orchestration tooling
can actually detect the failure. `docker-compose.yml`'s backend service now
has a real `healthcheck` using this endpoint (via Python's own
`urllib.request`, not `curl` — not installed in the slim base image, and
not worth adding just for this), and the frontend's `depends_on` now waits
for backend to report healthy rather than just "started."

**Structured (JSON) logging:** `JsonFormatter` emits one JSON object per log
line (timestamp, level, logger, message, exception if present) instead of
a plain-text traceback dump — what a real log aggregator (CloudWatch,
Datadog, etc.) needs to parse fields instead of scraping text. Scoped
deliberately to this app's own loggers (the `app.*` hierarchy, e.g. the
poller's failure logs) via `logging.getLogger("app")`, not the root logger
— reformatting Uvicorn's own request-access logs is a separate concern,
and clobbering the root logger risks interfering with libraries that log
through it for their own reasons.

**Rate limiting:** a small hand-rolled `RateLimiter` (fixed window, per
client IP, in-memory) rather than pulling in a library like `slowapi`.
Chosen deliberately: the limiting logic here is genuinely simple, a
hand-rolled version is fully explainable in an interview in a way "I
imported a library" isn't, and it avoids a new dependency's compatibility
risk against this project's pinned (very current) library versions.
Applied via middleware scoped to `/api/*` only — `/health` stays exempt
(orchestrators poll it frequently and shouldn't be throttled) and
`/ws/vehicles` is a different ASGI scope entirely (WebSocket, not HTTP),
so the HTTP-only middleware never touches it regardless. **Explicitly not
sufficient for a real multi-instance deployment** — the in-memory counter
doesn't survive a restart or get shared across processes; a production
deployment with more than one backend instance would need a shared store
(e.g. Redis) instead. Documented here rather than silently overstating
what this actually protects against.

## Service alerts: a fourth MBTA data source, same pattern as predictions

**Chosen:** `GET /api/stops/{id}/alerts` proxies MBTA's `/alerts` endpoint
live (never persisted — same reasoning as predictions: only meaningful
while active), filtered to `filter[datetime]=NOW` so only currently-active
alerts show, sorted `-severity` so the most disruptive one leads.

**Why this matters beyond "another endpoint":** verified against real data,
Back Bay currently has an active severity-7 Orange Line suspension (Oak
Grove–Back Bay, shuttle bus replacement) — which plausibly explains the
earlier "Arriving now but miles away" bug report: with that segment
suspended, real vehicle/trip assignments near Back Bay are legitimately
unusual right now. Surfacing the alert turns a confusing anomaly into an
understood, explained one — exactly the kind of context a rider actually
needs and official apps lead with.

**Severity bucketing, not a raw 0–10 number:** the frontend (`alertFormat.js`)
groups MBTA's severity scale into three bands (severe/moderate/minor) for
color-coding, rather than surfacing the raw integer — a rider needs "how
much should I care," not a precise score to interpret themselves.

## Bug fix: stale predictions displayed as "Arriving now"

**Found live:** clicking a prediction showing "Arriving now" isolated a
vehicle that was actually miles from the stop. Root cause: `minutesUntil()`
computed `Math.max(0, Math.round(diffMs / 60000))` — clamping *any* negative
value (arrival time already in the past) to 0, with no distinction between
"10 seconds late, basically arriving" and "this prediction is 20 minutes
stale because the assigned vehicle is running very late." Both displayed
identically as "Arriving now."

**Fix:** `isStalePrediction()` treats a prediction as unreliable once its
time is more than 60 seconds in the past (a small grace window survives,
for normal clock/reporting lag) and `usePredictions` filters those out
before anything else sees them — so the predictions list, the arrival-time
formatting, and the route-highlighting derived from it all only ever see
predictions worth trusting.

**Caveat, stated honestly:** this fixes the specific clamping bug, but
doesn't guarantee MBTA's own real-time predictions are always perfectly
accurate — occasional live-transit-data imprecision is a real, upstream
limitation this app can't fully eliminate, only avoid compounding.

## Highlighting a stop's routes: derived from live predictions, not a stops↔routes table

**Context:** after adding stop search + predictions, the next ask was to
"single out" a searched stop's transit on the map — filter the system-wide
vehicle view down to just the routes actually serving that stop.

**Chosen:** the frontend derives the set of relevant route IDs directly from
the stop's own predictions response it already has (`distinctRouteIds()` in
`predictionFormat.js`), and filters the map's vehicle list to just those
routes. No new backend endpoint.

**Alternatives considered:** using the `stop_routes` junction table and
`Route` model that already exist in the schema (`StopRepositoryInterface`
even has `get_routes_for_stop()`). Rejected for now — that table has never
actually been populated; doing so would mean syncing route↔stop
associations from MBTA (e.g. `/routes?filter[stop]=`) as a new ingestion
step, for a static answer to a question live predictions already answer for
free. It's also arguably more correct: predictions reflect what's actually
being routed to serve the stop right now (detours, service changes), where
a static join only reflects the nominal schedule. Worth revisiting if a
"routes serving this stop" fact is ever needed independent of live data.

**Filtering, not dimming, when a highlight is active:** vehicles outside the
highlighted set are removed entirely rather than shown at reduced opacity.
Dimming would have looked reasonable for individual pins, but markers are
clustered (see "Marker clustering" above) — a cluster bubble merges many
vehicles into one circle, so there's no sensible way to partially dim
"some of the vehicles inside this bubble." Filtering sidesteps that
entirely and matches "singles out" more literally besides.

## Client-side speed estimation when MBTA doesn't report one

**Context:** direct follow-up after adding "updated Xs ago" freshness —
the vehicle shown had no MBTA-reported speed at all (common for
generic/shuttle vehicles), leaving a gap the popup couldn't fill.

**Chosen:** estimate it client-side from two consecutive position reports
— haversine distance between the last two points, divided by the time
between their `updated_at` timestamps — computed in `applyVehicleUpdate`
(`vehicleState.js`) at the exact moment a new position arrives, since the
previous position for that vehicle is already sitting right there in
state. Zero new backend work: no new endpoint, no new stored data, just
math over what was already flowing through.

**Deliberately a fallback, not a replacement:** only computed when
MBTA's own `speed` field is null — MBTA's figure reflects real
instrumentation and the actual road path; a two-point straight-line
estimate can't match that and shouldn't override it. Displayed as
"~X mph (estimated)", never presented as if it were MBTA's own figure.

**Guarded against jitter:** estimates aren't computed for reports less
than 3 seconds apart (below the app's own ~5s poll cadence) — GPS noise
at that scale would dominate the distance measurement and could produce a
confidently-wrong number, which is worse than showing nothing.

## Bug fix: header title nearly invisible in light mode

**Found live** on the deployed app: the "TransitSync" title looked
invisible against its dark header. Root cause: `.header h1` never declared
its own `color`, so it fell through — per-property, not per-rule — to a
leftover global `h1 { color: var(--text-h) }` rule still in `index.css`
from Vite's original scaffold template. `--text-h` flips between near-white
and near-black based on the visitor's OS `prefers-color-scheme`, so on a
system in light mode the title rendered as near-black text on a near-black
background. Fixed by declaring `color` explicitly on `.header h1` — a
deliberately fixed dark header should never depend on the visitor's system
theme in the first place.

## Vehicle popups: made actually useful, not just a static label

**Context:** direct feedback that the map marker popup was too sparse to
be useful. It previously showed only vehicle ID, route, and status text.

**Chosen:** the popup now shows speed (converted from MBTA's meters/second
to mph — nobody reads m/s at a glance), how long ago the position was last
updated (directly relevant after the earlier stale-prediction incident — a
rider can now judge data freshness themselves instead of trusting it
blindly), and a **"Track this vehicle"** button that isolates just that
vehicle on the map — the same mechanism a prediction click already used,
now reachable directly from the map itself too. Clicking it again (or the
new ✕ on the isolation banner) clears it, since there was previously no way
to undo an isolation that started from a map click rather than a prediction
row.

## Bug fix: bare `postgresql://` URLs crashing the app at startup

**Found deploying to Render:** the first real deploy against Neon crashed
immediately with `ModuleNotFoundError: No module named 'psycopg2'`. Root
cause: `DATABASE_URL` was set to the connection string exactly as every
Postgres host hands it out — `postgresql://...` — but SQLAlchemy defaults
that bare scheme to the `psycopg2` driver, which this project never
installed (only `psycopg`, v3). Locally this had been worked around by
remembering to manually edit the scheme to `postgresql+psycopg://`; on a
real host, that manual step got missed.

**Fix:** `normalize_database_url()` in `app/db/session.py` rewrites a bare
`postgresql://` URL to `postgresql+psycopg://` before it ever reaches
`create_engine`, so the connection string works exactly as given by Neon,
Render, Supabase, or any other host — no special edit required, and no way
to silently forget it again.

## Deployment target: Render (app hosting) + Neon (Postgres)

**Chosen:** Render's free tier for both the backend (Docker web service)
and frontend (static site), with an external free-tier Postgres (Neon or
Supabase) rather than Render's own Postgres.

**Why not Render's own Postgres:** its free tier has historically expired
after 90 days, requiring manual recreation — a bad fit for a portfolio
project meant to stay up indefinitely without maintenance. Neon/Supabase's
free tiers don't have that expiry.

**Prerequisite fix — `VITE_API_BASE_URL`:** the frontend's backend-URL
derivation (`backendOrigin()`) assumed frontend and backend always share a
host, with the backend on port 8000 — true for local dev and
docker-compose, false once they're deployed to separate domains entirely.
Added an explicit override env var so this works in both cases from the
same code path, rather than branching on "are we deployed."

**Known free-tier trade-off, stated honestly:** Render's free web services
spin down after 15 minutes of inactivity and take tens of seconds to wake
on the next request. While spun down, `VehiclePoller` isn't running, so
vehicle data goes stale until something wakes the service back up. This is
an accepted limitation of $0 hosting for a portfolio demo, not a bug —
worth knowing about rather than being surprised by during a live demo.

## Frontend: React + Vite + Leaflet (added as step 10, outside the original roadmap)

**Context:** the original planning session's roadmap (`CLAUDE.md`) never
included a frontend layer at all, despite the project being described as a
"dashboard" — steps 1–9 only ever covered the backend. This gap surfaced
once the backend was actually working end-to-end and there was no way to
*see* it. Treated as a new, explicit step rather than silently squeezed into
an existing one.

**Chosen:** a separate React app (via Vite, not Create React App — Vite is
the current standard, with a much faster dev server) using `react-leaflet`
(a React wrapper around Leaflet) for the map, with free OpenStreetMap tiles.

**Alternatives considered:**
- *A plain HTML/JS page with vanilla Leaflet, served directly by FastAPI*:
  simpler — no Node.js toolchain, no separate container, no build step. This
  was the recommended default given the project's "simplest design that
  works" and $0-budget constraints, but a proper React/Vite split was chosen
  deliberately for being closer to how a real frontend/backend-split project
  is portfolio-presented, accepting the added complexity (Node.js install,
  a second Docker service, an `npm` toolchain) as a worthwhile trade.
- *Mapbox / Google Maps* instead of Leaflet+OpenStreetMap: rejected outright
  — both require an API key and have paid tiers past a free quota, which
  risks violating the $0 budget constraint if usage ever grew; OpenStreetMap
  tiles are free with no key required.
- *TypeScript*: deferred for this pass to keep the amount of new material
  (React itself, plus Vite, plus Leaflet) manageable in one step; the code
  is written in a style that would translate to TypeScript easily later.

## Marker clustering + status-color coding, not raw pins

**Context:** the first working version of the map plotted one default blue
Leaflet pin per vehicle. Tested live against real MBTA data (~550 vehicles
system-wide), it rendered as an unreadable, overlapping blob with no way to
tell what any given pin represented — confirmed by actually looking at it in
a browser, not assumed.

**Chosen:** `react-leaflet-cluster` groups nearby markers into a single
numbered bubble that splits apart as you zoom in, and each individual marker
is a small colored circle (a Leaflet `divIcon`, not the default pin) keyed
to `current_status` (moving / stopped / approaching), with a `Legend`
component explaining what the colors mean.

**Why:** clustering is the standard fix for "too many map markers to read"
— it's not a workaround, it's how every production map with this data
density (transit apps, ride-share apps) handles it. Color-coding by status
uses data already flowing through the pipeline (no backend change needed)
to make each marker individually meaningful instead of decorative. Dropping
the default pin image entirely also removed the earlier `_getIconUrl`
bundler workaround, since a `divIcon` has no external image dependency at
all — a case where the "better UX" choice was also the simpler code.

## WebSocket URL: derived from the page's own host, not hardcoded

**Chosen:** `useVehicleWebSocket.js` builds the WebSocket URL from
`window.location.hostname` (the address actually used to load the page) if
`VITE_WS_URL` isn't set, rather than hardcoding `localhost`.

**Why:** hardcoding `localhost` would only ever work when the browser and
the backend are the same machine. Since `window.location.hostname` is
whatever address the *browser* used to load the page, a phone or another PC
on the same network loading the dashboard via the host machine's LAN IP
(e.g. `http://192.168.1.50:5173`) gets a WebSocket connection to
`ws://192.168.1.50:8000/ws/vehicles` automatically — no per-device
configuration needed to satisfy "view it from another computer."

## Serving the built frontend with nginx, not Vite's dev server or Node

**Chosen:** `frontend/Dockerfile` builds the production bundle with Node in
one stage, then serves the resulting static files with `nginx:alpine` in the
final image — no Node.js in the image that actually runs.

**Why:** Vite's dev server is explicitly not meant for anything but local
development (no production hardening, rebuilds on every file change). Once
there's a static bundle, serving it needs nothing more than a file server;
nginx is small, fast, and battle-tested for exactly this, and mirrors the
same "don't ship the build toolchain in the runtime image" reasoning as the
backend's multi-stage Dockerfile.

## Testing: pytest + in-memory SQLite, not a live Postgres in CI

**Chosen:** repository/unit tests run against a fresh in-memory SQLite database
per test (`tests/conftest.py`), not a real Postgres instance.

**Alternatives considered:** a containerized Postgres for tests (e.g. via
`testcontainers`). Rejected for now — adds CI complexity and runtime for
marginal benefit, since the Repository pattern means the code under test
doesn't know which database it's talking to. Worth revisiting once
Postgres-specific features (e.g. `ilike`, JSON columns) are used in ways SQLite
can't emulate.

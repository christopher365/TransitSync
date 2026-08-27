# TransitSync — Project Context

This file gives Claude Code standing context for this repository. It was generated from a planning session in Claude (Cowork) on 2026-08-19 — see that conversation for the full discussion behind these decisions.

## What this project is

A real-time transit telemetry dashboard integrating the MBTA V3 API (pivoted from the original Metra GTFS-Realtime + OSU CABS plan — see "Data source" in `docs/architecture-decisions.md` for why), using Python, FastAPI, and WebSockets. Target: sub-500ms data sync to clients under 1,000+ mock concurrent users, an automated ingestion pipeline processing 10,000+ daily GPS coordinates into PostgreSQL, containerized with Docker and deployed via GitHub Actions CI/CD.

Treat the metrics above as real requirements to design and measure toward, not just descriptive text.

## Constraints (drive every design decision — see full rationale in `docs/architecture-decisions.md` and `01-project-charter.md` if present, or ask the developer)

- **Timeline:** a few weeks to a usable v1 — bias toward the simplest design that works end-to-end; defer nice-to-haves.
- **Team:** solo developer (Christopher, GitHub: christopher365), CS undergrad, intermediate — has prior Python/FastAPI/WebSocket/Postgres/Docker exposure. Comfortable moving at a normal pace, but still wants the "why" behind non-obvious decisions.
- **Budget:** $0 — free tiers only (e.g. Neon/Supabase free Postgres, local Docker Desktop, GitHub Actions free minutes). No paid cloud VM for v1.
- **Data consistency:** eventual consistency is fine — a few seconds of staleness in vehicle position is acceptable. Do NOT over-engineer with distributed locks, exactly-once delivery, or a full event-streaming platform (e.g. Kafka). A poll → ingest → broadcast pattern over WebSockets is sufficient.
- **Environment:** Windows PC ("horchata-cm") is primary, a MacBook is available as secondary — keep tooling cross-platform (Docker is the equalizer). Python 3.14 and Git 2.55 are installed on the Windows machine; Docker install is deliberately deferred until the containerization step, not needed for early layers.

## Working agreements / coding standards

- Build one architectural layer at a time: constraints → environment/repo → high-level architecture → database schema → ingestion pipeline → API/WebSocket layer → containerization/CI-CD. Don't jump ahead of the current layer.
- Enforce SOLID principles, DRY, and separation of concerns; call out violations explicitly rather than silently fixing them.
- Production-grade error handling and input validation even in v1 — this is meant to be portfolio-quality code, not throwaway scripts.
- Documentation/comments should explain *intent*, not just restate what the code does.
- Every major architectural decision should come with a brief comparative trade-off note (what else was considered, why this was chosen given the constraints above) rather than a silent choice — see `docs/architecture-decisions.md`.
- Use industry-standard multi-return / early-return (guard clause) style; do not force a single-return-per-function shape.

## Roadmap status

1. ✅ Define project constraints & requirements
2. ✅ Connect local project folder (`C:\Users\cm275\TransitSync`)
3. ✅ Verify/set up local dev tooling (Python 3.14, Git 2.55 confirmed installed; Docker still deferred to step 9)
4. ✅ Choose high-level architecture & tech stack — see `docs/architecture-decisions.md` for the trade-off notes (FastAPI, Postgres + SQLAlchemy 2.0 + Alembic, Repository pattern, poll→ingest→broadcast, MBTA as data source)
5. ✅ Scaffold repository structure & Git init (`backend/app/...`, first commit made 2026-08-25)
6. ✅ Design database schema (PostgreSQL) — `routes`, `stops`, `stop_routes` (static reference data) and `vehicle_positions` (append-only GPS log) all in place
7. ✅ Build data ingestion pipeline layer — `MbtaClient` + `VehicleIngestionService` poll MBTA `/vehicles` and record into `vehicle_positions`
8. ✅ Build FastAPI + WebSocket real-time API layer — `app/main.py`'s `/ws/vehicles` endpoint, `VehiclePoller` (5s interval, async-to-sync bridge via `asyncio.to_thread`), `ConnectionManager` broadcast, `VehiclePositionOut` schema
9. ✅ Containerize & set up CI/CD — WSL2 + Docker Desktop installed 2026-08-26 (per-user install, at `%LOCALAPPDATA%\Programs\DockerDesktop`; open a fresh terminal or re-source PATH before running `docker` — the installer updates the User PATH registry value but running sessions started beforehand won't see it). `docker compose up --build` verified end-to-end: real MBTA data polled, written to Postgres, and streamed live to a WebSocket client. Pushed to `https://github.com/christopher365/TransitSync` (public) on branch `main` 2026-08-26 — `.github/workflows/ci.yml` should now run for real on GitHub. Schema bootstrap still uses `Base.metadata.create_all()`, not Alembic — see `docs/architecture-decisions.md`.

10. ✅ Build a frontend dashboard — NOT part of the original planning session's roadmap (steps 1-9 only ever covered the backend); added 2026-08-26 once the backend was working end-to-end and there was no way to see it. React + Vite + react-leaflet (OpenStreetMap tiles, no API key/cost), served via nginx in its own Docker service. Verified live in a real browser against real MBTA data (~550 vehicles): the first pass (one default pin per vehicle) was an unreadable overlapping blob, so it was replaced with `react-leaflet-cluster` marker clustering + status-colored circle markers + a Legend, based on what that live test actually showed. See "Frontend" and "Marker clustering" in `docs/architecture-decisions.md`.

11. ✅ Add stop search + arrival predictions — added 2026-08-26 after direct feedback that the system-wide vehicle map, even clustered and color-coded, had no real purpose. New MBTA data sources (`/stops`, `/predictions`), a one-shot `StopSyncService` (265 real subway/light-rail stops synced at startup), and the app's first plain REST endpoints (`GET /api/stops?q=`, `GET /api/stops/{id}/predictions`) alongside the existing WebSocket. Frontend: a sidebar with stop search + a live (15s-polled) predictions panel, MBTA-line-colored route badges, and a distinct marker + fly-to for the selected stop. Verified against real MBTA data. See "Stop search + arrival predictions" in `docs/architecture-decisions.md`.

**v1 (backend + frontend, including stop search/predictions) is functionally complete end-to-end and on GitHub.** Remaining open items: decide on a free-tier Postgres host (Neon/Supabase) for anything beyond local Docker, and optionally a real Alembic baseline migration once that host exists.

Update this section as steps complete so future sessions (in either Claude Code or Claude/Cowork) know where the project actually stands.

# TransitSync

A real-time transit telemetry dashboard for Boston's MBTA system. It continuously polls live vehicle coordinates, streams updates over WebSockets to an interactive map, and logs GPS telemetry directly into PostgreSQL.

Built to handle high-frequency data streams end-to-end — an ingestion pipeline, a real-time API layer, and a frontend that turns raw positions into something a rider can actually use, not just a live map: stop search, arrival predictions, and service alerts.

**Live demo:** [transitsync-frontend.onrender.com](https://transitsync-frontend.onrender.com) (backend API: [transitsync-backend.onrender.com](https://transitsync-backend.onrender.com), health check at `/health`)

> Running on Render's free tier: the backend spins down after 15 minutes of inactivity and takes ~30-50 seconds to wake up on the next visit. If the map looks empty at first, give it a moment.

<!-- Add a screenshot or GIF here once you have one, e.g.: ![TransitSync screenshot](docs/screenshot.png) -->

## Features

- **Live vehicle tracking** — polls the MBTA V3 API and broadcasts every subway/light-rail vehicle system-wide over a WebSocket every 5 seconds.
- **Map clustering** — `react-leaflet-cluster` keeps dense downtown routes legible instead of an unreadable wall of pins.
- **Stop search, arrival predictions, and service alerts** — search any of 260+ synced stops, see live predicted arrivals (polled every 15s), and active MBTA service alerts for that stop.
- **Route and vehicle isolation** — selecting a stop filters the map to just the routes serving it; clicking a specific prediction isolates that one vehicle and flies the map to it.
- **Append-only ingestion pipeline** — every polled GPS coordinate is logged into PostgreSQL, not just the latest position: real historical telemetry, not a cache.
- **Production hardening** — a `/health` endpoint with real database connectivity checks, structured JSON logging, and rate limiting on the public API.

## Tech stack

| Layer | Stack |
|---|---|
| Backend | Python 3.14, FastAPI, WebSockets, SQLAlchemy 2.0, pytest |
| Frontend | React 19, Vite, Leaflet, Vitest |
| Database | PostgreSQL 16 (psycopg3) |
| Infrastructure | Docker + Docker Compose, GitHub Actions CI/CD, Render (hosting), Neon (managed Postgres) |

See [`docs/architecture-decisions.md`](docs/architecture-decisions.md) for the reasoning behind every major choice above — what else was considered and why, not just what was picked.

## Running locally

The entire stack is containerized — you only need Docker Desktop installed.

```bash
git clone https://github.com/christopher365/TransitSync.git
cd TransitSync
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000 (interactive docs at `/docs`, free from FastAPI)
- Backend health check: http://localhost:8000/health

Optional: set `MBTA_API_KEY` in `docker-compose.yml`'s backend service if you have one — unauthenticated requests work fine, just at a lower rate limit.

## Running the tests

```bash
# Backend
cd backend
pip install -r requirements.txt
pytest

# Frontend
cd frontend
npm install
npm test
```

## Deployment

Deployed via a [Render Blueprint](render.yaml): a free web service for the backend (Docker), a free static site for the frontend, and an external free-tier Postgres on [Neon](https://neon.tech). Render's own free Postgres tier has historically expired after 90 days; Neon's doesn't.

## Project structure

```
backend/    FastAPI app — ingestion pipeline, REST + WebSocket API, tests
frontend/   React app — live map, stop search, predictions, alerts
docs/       Architecture decisions and trade-off notes
```

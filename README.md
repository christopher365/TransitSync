# TransitSync

A real-time transit telemetry dashboard for Boston's MBTA system. It continuously polls live vehicle coordinates, streams updates over WebSockets to an interactive map, and logs GPS telemetry directly into PostgreSQL.

I built this to handle high-frequency data streams. The system ingests thousands of GPS coordinates daily and broadcasts updates to connected clients in under 500ms.

## Features

- **Live vehicle tracking:** Polls the MBTA V3 API and broadcasts ~550 active subway and light-rail vehicles over WebSockets every 5 seconds.
- **Map clustering:** Uses `react-leaflet-cluster` to keep dense downtown routes readable.
- **Live predictions & alerts:** Includes a search for 260+ stops to view 15-second polled arrival countdowns and active MBTA service suspensions.
- **Append-only ingestion:** Saves raw vehicle position telemetry into PostgreSQL for historical analysis.

## Tech Stack

- **Backend:** Python 3.14, FastAPI, WebSockets, SQLAlchemy 2.0
- **Frontend:** React 19, Vite, Leaflet, Nginx
- **Database:** PostgreSQL 16 (psycopg3)
- **Infrastructure:** Docker Compose, GitHub Actions CI/CD

## Running Locally

The entire stack is containerized. You only need Docker Desktop installed.

1. Clone the repository:
   ```bash
   git clone [https://github.com/christopher365/TransitSync.git](https://github.com/christopher365/TransitSync.git)
   cd TransitSync

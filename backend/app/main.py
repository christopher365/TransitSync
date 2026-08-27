import asyncio
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import configure_logging
from app.core.rate_limit import RateLimiter
from app.db.base import Base
from app.db.models import VehiclePosition
from app.db.repositories.stop_repository import SqlAlchemyStopRepository
from app.db.repositories.vehicle_position_repository import SqlAlchemyVehiclePositionRepository
from app.db.session import SessionLocal, engine as default_engine, session_scope
from app.ingestion.mbta_client import MbtaClient
from app.ingestion.stop_sync_service import StopSyncService
from app.ingestion.vehicle_ingestion_service import VehicleIngestionService
from app.realtime.connection_manager import ConnectionManager
from app.realtime.poller import VehiclePoller
from app.schemas.alert import AlertOut
from app.schemas.prediction import PredictionOut
from app.schemas.stop import StopOut
from app.schemas.vehicle_position import VehiclePositionOut

configure_logging()
logger = logging.getLogger(__name__)

# Applies to the REST endpoints under /api/ only — not /health (load
# balancers/orchestrators poll it frequently and shouldn't be throttled)
# and not /ws/vehicles (a WebSocket connection isn't a repeated request in
# the same sense; ConnectionManager already bounds it to one entry per
# client). 30 requests/minute comfortably covers legitimate debounced
# search typing while still doing something under actual abuse.
DEFAULT_RATE_LIMIT_MAX_REQUESTS = 30
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60.0


def create_app(
    engine: Engine = default_engine,
    session_factory: Callable[[], Session] = SessionLocal,
    mbta_client: MbtaClient | None = None,
    poll_fn: Callable[[], list[VehiclePosition]] | None = None,
    poll_interval_seconds: float = 5.0,
    rate_limiter: RateLimiter | None = None,
) -> FastAPI:
    """Application factory: builds a fresh app (and everything it depends
    on) from scratch, rather than relying on module-level globals.

    This is what lets tests build an app wired to an in-memory SQLite
    database and a poll_fn/mbta_client that never touch the network, instead
    of the real Postgres + MBTA API the production app uses — without either
    version needing a single "if we're testing" branch anywhere.
    """
    if mbta_client is None:
        mbta_client = MbtaClient(base_url=settings.mbta_api_base_url, api_key=settings.mbta_api_key)

    if rate_limiter is None:
        rate_limiter = RateLimiter(
            max_requests=DEFAULT_RATE_LIMIT_MAX_REQUESTS,
            window_seconds=DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
        )

    connection_manager = ConnectionManager()

    if poll_fn is None:

        def poll_fn() -> list[VehiclePosition]:
            with session_scope(session_factory) as session:
                repository = SqlAlchemyVehiclePositionRepository(session)
                return VehicleIngestionService(mbta_client, repository).run_once()

    def fetch_all_latest_positions() -> list[VehiclePosition]:
        with session_scope(session_factory) as session:
            return SqlAlchemyVehiclePositionRepository(session).get_all_latest_positions()

    def sync_stops() -> None:
        with session_scope(session_factory) as session:
            repository = SqlAlchemyStopRepository(session)
            StopSyncService(mbta_client, repository).sync()

    def get_session():
        with session_scope(session_factory) as session:
            yield session

    poller = VehiclePoller(
        poll_fn=poll_fn,
        connection_manager=connection_manager,
        interval_seconds=poll_interval_seconds,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Stand-in for a real Alembic migration until a live Postgres exists
        # to autogenerate one against (see docs/architecture-decisions.md).
        # Safe to call every startup: create_all only creates tables that
        # don't already exist yet.
        Base.metadata.create_all(bind=engine)

        try:
            await asyncio.to_thread(sync_stops)
        except Exception:
            # Stop search just returns no results until this succeeds on a
            # later restart; it shouldn't stop the whole app from serving
            # the (more important) live vehicle map.
            logger.exception("Stop sync failed at startup; stop search will return no results")

        poller.start()
        yield
        await poller.stop()

    app = FastAPI(lifespan=lifespan)

    # No cookies or auth are involved (this only ever serves public transit
    # data), so allowing any origin is low-risk and avoids having to keep an
    # allowlist in sync with wherever the frontend happens to be hosted.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if request.url.path.startswith("/api/"):
            client_key = request.client.host if request.client else "unknown"
            if not rate_limiter.is_allowed(client_key):
                return JSONResponse(status_code=429, content={"detail": "Too many requests"})
        return await call_next(request)

    @app.get("/health")
    def health_check(response: Response) -> dict[str, str]:
        try:
            with session_scope(session_factory) as session:
                session.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception:
            db_status = "unreachable"

        if db_status != "ok":
            response.status_code = 503

        return {"status": "ok" if db_status == "ok" else "error", "db": db_status}

    @app.websocket("/ws/vehicles")
    async def vehicle_positions_ws(websocket: WebSocket) -> None:
        await connection_manager.connect(websocket)
        try:
            initial_positions = await asyncio.to_thread(fetch_all_latest_positions)
            for position in initial_positions:
                payload = VehiclePositionOut.model_validate(position).model_dump(mode="json")
                await websocket.send_json(payload)

            while True:
                # Clients don't send us anything meaningful; this just
                # blocks until the client disconnects, which is what raises
                # WebSocketDisconnect below.
                await websocket.receive_text()
        except WebSocketDisconnect:
            connection_manager.disconnect(websocket)

    @app.get("/api/stops", response_model=list[StopOut])
    def search_stops(q: str = "", session: Session = Depends(get_session)) -> list[StopOut]:
        if not q or not q.strip():
            return []

        repository = SqlAlchemyStopRepository(session)
        return repository.search_by_name(q)

    @app.get("/api/stops/{stop_id}/predictions", response_model=list[PredictionOut])
    def get_stop_predictions(stop_id: str) -> list[PredictionOut]:
        # A plain (non-async) FastAPI route handler like this one is
        # automatically run in a worker thread by Starlette, the same way
        # asyncio.to_thread is used explicitly elsewhere in this file — so
        # this blocking HTTP call doesn't need that wrapping here too.
        return mbta_client.get_predictions(stop_id)

    @app.get("/api/stops/{stop_id}/alerts", response_model=list[AlertOut])
    def get_stop_alerts(stop_id: str) -> list[AlertOut]:
        return mbta_client.get_alerts(stop_id)

    return app


app = create_app()

import asyncio
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
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
from app.schemas.prediction import PredictionOut
from app.schemas.stop import StopOut
from app.schemas.vehicle_position import VehiclePositionOut

logger = logging.getLogger(__name__)


def create_app(
    engine: Engine = default_engine,
    session_factory: Callable[[], Session] = SessionLocal,
    mbta_client: MbtaClient | None = None,
    poll_fn: Callable[[], list[VehiclePosition]] | None = None,
    poll_interval_seconds: float = 5.0,
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

    return app


app = create_app()

import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import VehiclePosition
from app.db.repositories.vehicle_position_repository import SqlAlchemyVehiclePositionRepository
from app.db.session import SessionLocal, session_scope
from app.ingestion.mbta_client import MbtaClient
from app.ingestion.vehicle_ingestion_service import VehicleIngestionService
from app.realtime.connection_manager import ConnectionManager
from app.realtime.poller import VehiclePoller
from app.schemas.vehicle_position import VehiclePositionOut


def create_app(
    session_factory: Callable[[], Session] = SessionLocal,
    poll_fn: Callable[[], list[VehiclePosition]] | None = None,
    poll_interval_seconds: float = 5.0,
) -> FastAPI:
    """Application factory: builds a fresh app (and everything it depends
    on) from scratch, rather than relying on module-level globals.

    This is what lets tests build an app wired to an in-memory SQLite
    database and a poll_fn that never touches the network, instead of the
    real Postgres + MBTA API the production app uses — without either
    version needing a single "if we're testing" branch anywhere.
    """
    connection_manager = ConnectionManager()

    if poll_fn is None:
        mbta_client = MbtaClient(base_url=settings.mbta_api_base_url, api_key=settings.mbta_api_key)

        def poll_fn() -> list[VehiclePosition]:
            with session_scope(session_factory) as session:
                repository = SqlAlchemyVehiclePositionRepository(session)
                return VehicleIngestionService(mbta_client, repository).run_once()

    def fetch_all_latest_positions() -> list[VehiclePosition]:
        with session_scope(session_factory) as session:
            return SqlAlchemyVehiclePositionRepository(session).get_all_latest_positions()

    poller = VehiclePoller(
        poll_fn=poll_fn,
        connection_manager=connection_manager,
        interval_seconds=poll_interval_seconds,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        poller.start()
        yield
        await poller.stop()

    app = FastAPI(lifespan=lifespan)

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

    return app


app = create_app()

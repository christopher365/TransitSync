from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import VehiclePosition
from app.main import create_app


def build_test_app(poll_fn=None):
    """An in-memory SQLite database shared across every session it hands
    out, via StaticPool + check_same_thread=False.

    Without StaticPool, each `session_factory()` call would open its own
    private, empty `:memory:` database — SQLite's in-memory databases are
    normally per-connection, not shared. check_same_thread=False is needed
    because our app code deliberately runs DB work on a worker thread
    (asyncio.to_thread), and SQLite refuses to reuse a connection across
    threads by default.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    app = create_app(
        engine=engine,
        session_factory=session_factory,
        poll_fn=poll_fn if poll_fn is not None else (lambda: []),
    )
    return app, session_factory


def test_websocket_sends_existing_positions_immediately_on_connect() -> None:
    app, session_factory = build_test_app()
    session = session_factory()
    now = datetime.now(timezone.utc)
    session.add(
        VehiclePosition(
            vehicle_id="y1",
            route_id="Red",
            trip_id=None,
            latitude=42.0,
            longitude=-71.0,
            bearing=None,
            speed=None,
            current_status="STOPPED_AT",
            updated_at=now,
            recorded_at=now,
        )
    )
    session.commit()
    session.close()

    with TestClient(app) as client:
        with client.websocket_connect("/ws/vehicles") as websocket:
            message = websocket.receive_json()

    assert message["vehicle_id"] == "y1"
    assert message["current_status"] == "STOPPED_AT"


def test_websocket_connects_cleanly_with_no_existing_positions() -> None:
    app, _ = build_test_app()

    with TestClient(app) as client:
        with client.websocket_connect("/ws/vehicles") as websocket:
            websocket.close()

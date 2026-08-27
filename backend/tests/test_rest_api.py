from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.ingestion.dto import PredictionReading, StopReading
from app.main import create_app
from tests.support import StubMbtaClient


def build_test_app(mbta_client=None):
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
        mbta_client=mbta_client if mbta_client is not None else StubMbtaClient(),
        poll_fn=lambda: [],
    )
    return app


def test_startup_syncs_stops_and_search_finds_them() -> None:
    stub_client = StubMbtaClient(
        stops=[
            StopReading(
                stop_id="place-pktrm",
                name="Park Street",
                latitude=42.3564,
                longitude=-71.0624,
                wheelchair_boarding=1,
            )
        ]
    )
    app = build_test_app(mbta_client=stub_client)

    with TestClient(app) as client:
        response = client.get("/api/stops", params={"q": "park"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "place-pktrm"
    assert body[0]["name"] == "Park Street"


def test_search_stops_returns_empty_list_for_blank_query() -> None:
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/api/stops", params={"q": ""})

    assert response.status_code == 200
    assert response.json() == []


def test_search_stops_returns_empty_list_when_nothing_matches() -> None:
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/api/stops", params={"q": "nonexistent"})

    assert response.status_code == 200
    assert response.json() == []


def test_get_predictions_returns_mbta_client_results() -> None:
    now = datetime.now(timezone.utc)
    stub_client = StubMbtaClient(
        predictions=[
            PredictionReading(
                route_id="Red",
                trip_id="trip-1",
                vehicle_id="y1234",
                arrival_time=now,
                departure_time=None,
                status=None,
            )
        ]
    )
    app = build_test_app(mbta_client=stub_client)

    with TestClient(app) as client:
        response = client.get("/api/stops/place-pktrm/predictions")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["route_id"] == "Red"
    assert body[0]["vehicle_id"] == "y1234"


def test_get_predictions_returns_empty_list_when_none_available() -> None:
    app = build_test_app()

    with TestClient(app) as client:
        response = client.get("/api/stops/place-pktrm/predictions")

    assert response.status_code == 200
    assert response.json() == []

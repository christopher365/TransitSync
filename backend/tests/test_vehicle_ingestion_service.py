from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.repositories.vehicle_position_repository import SqlAlchemyVehiclePositionRepository
from app.ingestion.dto import VehicleReading
from app.ingestion.vehicle_ingestion_service import VehicleIngestionService


class StubMbtaClient:
    """A test double standing in for MbtaClient — returns canned readings
    instead of making a real HTTP call, so this test is about the service's
    own logic, not MBTA's API or the network.
    """

    def __init__(self, readings: list[VehicleReading]) -> None:
        self._readings = readings

    def get_vehicles(self) -> list[VehicleReading]:
        return self._readings


def make_reading(vehicle_id: str = "y1234") -> VehicleReading:
    return VehicleReading(
        vehicle_id=vehicle_id,
        route_id="Red",
        trip_id="trip-1",
        latitude=42.3564,
        longitude=-71.0624,
        bearing=90.0,
        speed=5.0,
        current_status="IN_TRANSIT_TO",
        updated_at=datetime.now(timezone.utc),
    )


def test_run_once_records_every_reading(db_session: Session) -> None:
    stub_client = StubMbtaClient([make_reading("y1"), make_reading("y2")])
    repository = SqlAlchemyVehiclePositionRepository(db_session)
    service = VehicleIngestionService(stub_client, repository)

    ingested_count = service.run_once()

    assert ingested_count == 2
    assert repository.get_latest_for_vehicle("y1") is not None
    assert repository.get_latest_for_vehicle("y2") is not None


def test_run_once_returns_zero_when_no_vehicles_reported(db_session: Session) -> None:
    stub_client = StubMbtaClient([])
    repository = SqlAlchemyVehiclePositionRepository(db_session)
    service = VehicleIngestionService(stub_client, repository)

    ingested_count = service.run_once()

    assert ingested_count == 0

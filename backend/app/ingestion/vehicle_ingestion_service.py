from app.db.models import VehiclePosition
from app.db.repositories.interfaces import VehiclePositionRepositoryInterface
from app.ingestion.mbta_client import MbtaClient


class VehicleIngestionService:
    """Orchestrates one poll → ingest cycle: fetch current vehicles from
    MBTA, persist each as a VehiclePosition row. Depends on interfaces
    (MbtaClient's public shape, VehiclePositionRepositoryInterface) so it
    can be tested without a real network call or a real Postgres.
    """

    def __init__(
        self,
        mbta_client: MbtaClient,
        repository: VehiclePositionRepositoryInterface,
    ) -> None:
        self._mbta_client = mbta_client
        self._repository = repository

    def run_once(self) -> list[VehiclePosition]:
        """Runs a single poll cycle and returns every position recorded, so
        callers (e.g. the WebSocket broadcaster) know exactly what's new.
        """
        readings = self._mbta_client.get_vehicles()
        recorded_positions = []

        for reading in readings:
            position = VehiclePosition(
                vehicle_id=reading.vehicle_id,
                route_id=reading.route_id,
                trip_id=reading.trip_id,
                latitude=reading.latitude,
                longitude=reading.longitude,
                bearing=reading.bearing,
                speed=reading.speed,
                current_status=reading.current_status,
                updated_at=reading.updated_at,
            )
            recorded_positions.append(self._repository.record(position))

        return recorded_positions

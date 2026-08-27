from app.db.models import Stop
from app.db.repositories.interfaces import StopRepositoryInterface
from app.ingestion.mbta_client import MbtaClient


class StopSyncService:
    """Syncs MBTA's stop reference data into our own `stops` table.

    Unlike VehicleIngestionService, this isn't meant to run on a repeating
    poll — stops rarely change, so this runs once (at app startup) rather
    than every few seconds. upsert() makes re-running it at any time safe.
    """

    def __init__(self, mbta_client: MbtaClient, repository: StopRepositoryInterface) -> None:
        self._mbta_client = mbta_client
        self._repository = repository

    def sync(self) -> list[Stop]:
        readings = self._mbta_client.get_stops()
        synced_stops = []

        for reading in readings:
            stop = Stop(
                id=reading.stop_id,
                name=reading.name,
                latitude=reading.latitude,
                longitude=reading.longitude,
                wheelchair_boarding=reading.wheelchair_boarding,
            )
            synced_stops.append(self._repository.upsert(stop))

        return synced_stops

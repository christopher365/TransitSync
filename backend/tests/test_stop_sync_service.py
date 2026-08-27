from sqlalchemy.orm import Session

from app.db.repositories.stop_repository import SqlAlchemyStopRepository
from app.ingestion.dto import StopReading
from app.ingestion.stop_sync_service import StopSyncService


class StubMbtaClient:
    def __init__(self, stops: list[StopReading]) -> None:
        self._stops = stops

    def get_stops(self) -> list[StopReading]:
        return self._stops


def make_stop_reading(stop_id: str = "place-pktrm", name: str = "Park Street") -> StopReading:
    return StopReading(
        stop_id=stop_id, name=name, latitude=42.3564, longitude=-71.0624, wheelchair_boarding=1
    )


def test_sync_upserts_every_stop_returned(db_session: Session) -> None:
    stub_client = StubMbtaClient([make_stop_reading("s1"), make_stop_reading("s2")])
    repository = SqlAlchemyStopRepository(db_session)
    service = StopSyncService(stub_client, repository)

    synced = service.sync()

    assert {s.id for s in synced} == {"s1", "s2"}
    assert repository.get_by_id("s1") is not None
    assert repository.get_by_id("s2") is not None


def test_sync_updates_existing_stop_instead_of_duplicating(db_session: Session) -> None:
    stub_client = StubMbtaClient([make_stop_reading(name="Park St (old name)")])
    repository = SqlAlchemyStopRepository(db_session)
    StopSyncService(stub_client, repository).sync()

    stub_client_v2 = StubMbtaClient([make_stop_reading(name="Park Street")])
    StopSyncService(stub_client_v2, repository).sync()

    matches = repository.search_by_name("Park")
    assert len(matches) == 1
    assert matches[0].name == "Park Street"


def test_sync_returns_empty_list_when_no_stops_reported(db_session: Session) -> None:
    service = StopSyncService(StubMbtaClient([]), SqlAlchemyStopRepository(db_session))

    assert service.sync() == []

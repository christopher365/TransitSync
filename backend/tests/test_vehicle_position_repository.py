from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.db.models import VehiclePosition
from app.db.repositories.vehicle_position_repository import SqlAlchemyVehiclePositionRepository


def make_position(
    vehicle_id: str = "y1234",
    route_id: str | None = "Red",
    recorded_at: datetime | None = None,
) -> VehiclePosition:
    return VehiclePosition(
        vehicle_id=vehicle_id,
        route_id=route_id,
        trip_id="trip-1",
        latitude=42.3564,
        longitude=-71.0624,
        bearing=90.0,
        speed=5.0,
        current_status="IN_TRANSIT_TO",
        updated_at=recorded_at or datetime.now(timezone.utc),
        recorded_at=recorded_at or datetime.now(timezone.utc),
    )


def test_record_raises_on_empty_vehicle_id(db_session: Session) -> None:
    repo = SqlAlchemyVehiclePositionRepository(db_session)

    with pytest.raises(ValueError):
        repo.record(make_position(vehicle_id="  "))


def test_record_inserts_a_new_row_each_call(db_session: Session) -> None:
    repo = SqlAlchemyVehiclePositionRepository(db_session)

    repo.record(make_position())
    repo.record(make_position())

    latest = repo.get_latest_for_vehicle("y1234")
    assert latest is not None
    all_for_route = repo.get_latest_for_route("Red")
    assert len(all_for_route) == 1  # one vehicle, latest row only


def test_get_latest_for_vehicle_returns_none_when_not_found(db_session: Session) -> None:
    repo = SqlAlchemyVehiclePositionRepository(db_session)

    result = repo.get_latest_for_vehicle("does-not-exist")

    assert result is None


def test_get_latest_for_vehicle_raises_on_empty_id(db_session: Session) -> None:
    repo = SqlAlchemyVehiclePositionRepository(db_session)

    with pytest.raises(ValueError):
        repo.get_latest_for_vehicle("")


def test_get_latest_for_vehicle_returns_most_recent_report(db_session: Session) -> None:
    repo = SqlAlchemyVehiclePositionRepository(db_session)
    older = datetime.now(timezone.utc) - timedelta(minutes=5)
    newer = datetime.now(timezone.utc)
    repo.record(make_position(recorded_at=older))
    repo.record(make_position(recorded_at=newer))

    latest = repo.get_latest_for_vehicle("y1234")

    assert latest is not None
    # SQLite (used for this in-memory test) drops tzinfo on read-back even for
    # DateTime(timezone=True) columns; Postgres would not. Normalize before comparing.
    assert latest.recorded_at.replace(tzinfo=timezone.utc) == newer


def test_get_latest_for_route_raises_on_empty_id(db_session: Session) -> None:
    repo = SqlAlchemyVehiclePositionRepository(db_session)

    with pytest.raises(ValueError):
        repo.get_latest_for_route("")


def test_get_latest_for_route_returns_one_row_per_vehicle(db_session: Session) -> None:
    repo = SqlAlchemyVehiclePositionRepository(db_session)
    repo.record(make_position(vehicle_id="y1", route_id="Red"))
    repo.record(make_position(vehicle_id="y2", route_id="Red"))
    repo.record(make_position(vehicle_id="y3", route_id="Orange"))

    results = repo.get_latest_for_route("Red")

    assert {p.vehicle_id for p in results} == {"y1", "y2"}


def test_get_latest_for_route_returns_empty_list_when_no_vehicles(db_session: Session) -> None:
    repo = SqlAlchemyVehiclePositionRepository(db_session)

    results = repo.get_latest_for_route("does-not-exist")

    assert results == []

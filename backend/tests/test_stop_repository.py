import pytest
from sqlalchemy.orm import Session

from app.db.models import Route, Stop, StopRoute
from app.db.repositories.stop_repository import SqlAlchemyStopRepository


def make_stop(stop_id: str = "place-pktrm", name: str = "Park Street") -> Stop:
    return Stop(id=stop_id, name=name, latitude=42.3564, longitude=-71.0624, wheelchair_boarding=1)


def test_get_by_id_returns_none_when_not_found(db_session: Session) -> None:
    repo = SqlAlchemyStopRepository(db_session)

    result = repo.get_by_id("does-not-exist")

    assert result is None


def test_get_by_id_raises_on_empty_id(db_session: Session) -> None:
    repo = SqlAlchemyStopRepository(db_session)

    with pytest.raises(ValueError):
        repo.get_by_id("   ")


def test_upsert_inserts_new_stop(db_session: Session) -> None:
    repo = SqlAlchemyStopRepository(db_session)

    saved = repo.upsert(make_stop())

    assert saved.id == "place-pktrm"
    assert repo.get_by_id("place-pktrm") is not None


def test_upsert_updates_existing_stop_instead_of_duplicating(db_session: Session) -> None:
    repo = SqlAlchemyStopRepository(db_session)
    repo.upsert(make_stop(name="Park St (old name)"))

    updated = repo.upsert(make_stop(name="Park Street"))

    assert updated.name == "Park Street"
    all_matches = repo.search_by_name("Park")
    assert len(all_matches) == 1


def test_search_by_name_matches_case_insensitive_substring(db_session: Session) -> None:
    repo = SqlAlchemyStopRepository(db_session)
    repo.upsert(make_stop())

    results = repo.search_by_name("park street")

    assert len(results) == 1
    assert results[0].id == "place-pktrm"


def test_search_by_name_raises_on_empty_query(db_session: Session) -> None:
    repo = SqlAlchemyStopRepository(db_session)

    with pytest.raises(ValueError):
        repo.search_by_name("")


def test_get_routes_for_stop_returns_associated_routes(db_session: Session) -> None:
    repo = SqlAlchemyStopRepository(db_session)
    stop = make_stop()
    route = Route(id="Red", short_name="Red Line", long_name="Red Line", type=1)
    db_session.add_all([stop, route, StopRoute(stop_id=stop.id, route_id=route.id)])
    db_session.commit()

    routes = repo.get_routes_for_stop(stop.id)

    assert [r.id for r in routes] == ["Red"]


def test_get_routes_for_stop_returns_empty_list_when_stop_missing(db_session: Session) -> None:
    repo = SqlAlchemyStopRepository(db_session)

    routes = repo.get_routes_for_stop("does-not-exist")

    assert routes == []

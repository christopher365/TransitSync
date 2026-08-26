from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Route, Stop
from app.db.repositories.interfaces import StopRepositoryInterface


class SqlAlchemyStopRepository(StopRepositoryInterface):
    """SQLAlchemy-backed implementation of StopRepositoryInterface."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, stop_id: str) -> Stop | None:
        if not stop_id or not stop_id.strip():
            raise ValueError("stop_id must be a non-empty string")

        result = self._session.get(Stop, stop_id)
        return result

    def search_by_name(self, query: str, limit: int = 20) -> list[Stop]:
        if not query or not query.strip():
            raise ValueError("query must be a non-empty string")
        if limit <= 0:
            raise ValueError("limit must be a positive integer")

        statement = (
            select(Stop)
            .where(Stop.name.ilike(f"%{query.strip()}%"))
            .order_by(Stop.name)
            .limit(limit)
        )
        result = list(self._session.scalars(statement))
        return result

    def get_routes_for_stop(self, stop_id: str) -> list[Route]:
        stop = self.get_by_id(stop_id)

        if stop is None:
            result: list[Route] = []
        else:
            result = list(stop.routes)

        return result

    def upsert(self, stop: Stop) -> Stop:
        existing = self._session.get(Stop, stop.id)

        if existing is not None:
            existing.name = stop.name
            existing.latitude = stop.latitude
            existing.longitude = stop.longitude
            existing.wheelchair_boarding = stop.wheelchair_boarding
            existing.updated_at = datetime.now(timezone.utc)
            result = existing
        else:
            stop.updated_at = datetime.now(timezone.utc)
            self._session.add(stop)
            result = stop

        self._session.commit()
        return result

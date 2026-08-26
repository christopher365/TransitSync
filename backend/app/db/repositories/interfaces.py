from abc import ABC, abstractmethod

from app.db.models import Route, Stop


class StopRepositoryInterface(ABC):
    """Abstraction over stop persistence.

    Business logic (the layer above this one) depends on this interface,
    never on SQLAlchemy directly. See the Dependency Inversion Principle
    discussion alongside this file.
    """

    @abstractmethod
    def get_by_id(self, stop_id: str) -> Stop | None:
        raise NotImplementedError

    @abstractmethod
    def search_by_name(self, query: str, limit: int = 20) -> list[Stop]:
        raise NotImplementedError

    @abstractmethod
    def get_routes_for_stop(self, stop_id: str) -> list[Route]:
        raise NotImplementedError

    @abstractmethod
    def upsert(self, stop: Stop) -> Stop:
        raise NotImplementedError

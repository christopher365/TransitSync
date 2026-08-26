from abc import ABC, abstractmethod

from app.db.models import Route, Stop, VehiclePosition


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


class VehiclePositionRepositoryInterface(ABC):
    """Abstraction over vehicle position persistence.

    Kept separate from StopRepositoryInterface (Interface Segregation): the
    ingestion pipeline and the live API depend only on the position-reading
    and -recording operations they actually need.
    """

    @abstractmethod
    def record(self, position: VehiclePosition) -> VehiclePosition:
        raise NotImplementedError

    @abstractmethod
    def get_latest_for_vehicle(self, vehicle_id: str) -> VehiclePosition | None:
        raise NotImplementedError

    @abstractmethod
    def get_latest_for_route(self, route_id: str) -> list[VehiclePosition]:
        raise NotImplementedError

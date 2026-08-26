from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.models import VehiclePosition
from app.db.repositories.interfaces import VehiclePositionRepositoryInterface


class SqlAlchemyVehiclePositionRepository(VehiclePositionRepositoryInterface):
    """SQLAlchemy-backed implementation of VehiclePositionRepositoryInterface."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(self, position: VehiclePosition) -> VehiclePosition:
        if not position.vehicle_id or not position.vehicle_id.strip():
            raise ValueError("position.vehicle_id must be a non-empty string")

        self._session.add(position)
        self._session.commit()
        return position

    def get_latest_for_vehicle(self, vehicle_id: str) -> VehiclePosition | None:
        if not vehicle_id or not vehicle_id.strip():
            raise ValueError("vehicle_id must be a non-empty string")

        statement = (
            select(VehiclePosition)
            .where(VehiclePosition.vehicle_id == vehicle_id)
            .order_by(VehiclePosition.recorded_at.desc())
            .limit(1)
        )
        result = self._session.scalars(statement).first()
        return result

    def get_latest_for_route(self, route_id: str) -> list[VehiclePosition]:
        if not route_id or not route_id.strip():
            raise ValueError("route_id must be a non-empty string")

        latest_per_vehicle = (
            select(
                VehiclePosition.vehicle_id,
                func.max(VehiclePosition.recorded_at).label("max_recorded_at"),
            )
            .where(VehiclePosition.route_id == route_id)
            .group_by(VehiclePosition.vehicle_id)
            .subquery()
        )
        statement = select(VehiclePosition).join(
            latest_per_vehicle,
            and_(
                VehiclePosition.vehicle_id == latest_per_vehicle.c.vehicle_id,
                VehiclePosition.recorded_at == latest_per_vehicle.c.max_recorded_at,
            ),
        )
        result = list(self._session.scalars(statement))
        return result

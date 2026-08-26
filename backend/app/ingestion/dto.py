from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VehicleReading:
    """A vehicle position exactly as MBTA reported it, before it becomes a
    VehiclePosition database row.

    Kept separate from the ORM model so this module (and its tests) never
    needs to import SQLAlchemy, and so a future change to the DB schema
    doesn't ripple into the MBTA-parsing code, or vice versa.
    """

    vehicle_id: str
    route_id: str | None
    trip_id: str | None
    latitude: float
    longitude: float
    bearing: float | None
    speed: float | None
    current_status: str
    updated_at: datetime

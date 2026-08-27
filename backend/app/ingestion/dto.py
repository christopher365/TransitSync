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


@dataclass(frozen=True)
class StopReading:
    """A transit stop exactly as MBTA reported it, before it becomes a
    Stop database row. Same reasoning as VehicleReading above.
    """

    stop_id: str
    name: str
    latitude: float
    longitude: float
    wheelchair_boarding: int


@dataclass(frozen=True)
class PredictionReading:
    """A predicted arrival/departure at one stop.

    Never persisted — predictions are only meaningful for the next several
    minutes, so they're fetched fresh from MBTA on demand rather than stored
    like vehicle positions are.
    """

    route_id: str | None
    trip_id: str | None
    vehicle_id: str | None
    arrival_time: datetime | None
    departure_time: datetime | None
    status: str | None


@dataclass(frozen=True)
class AlertReading:
    """An active service alert (delay, detour, elevator outage, etc.).

    Never persisted, same reasoning as PredictionReading: only meaningful
    while active, so fetched fresh from MBTA rather than stored.
    """

    alert_id: str
    header: str
    effect: str | None
    severity: int | None
    cause: str | None

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VehiclePositionOut(BaseModel):
    """The wire format sent to WebSocket clients for one vehicle position.

    Deliberately mirrors VehiclePosition's fields but is a separate class:
    this is what we promise *clients* (a public contract), while the ORM
    model is free to change internally without silently changing that
    contract.
    """

    model_config = ConfigDict(from_attributes=True)

    vehicle_id: str
    route_id: str | None
    trip_id: str | None
    latitude: float
    longitude: float
    bearing: float | None
    speed: float | None
    current_status: str
    updated_at: datetime
    recorded_at: datetime

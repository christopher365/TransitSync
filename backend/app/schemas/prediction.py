from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PredictionOut(BaseModel):
    """The wire format for one arrival/departure prediction. Mirrors
    PredictionReading directly — from_attributes lets Pydantic read it
    (a plain dataclass, not an ORM model) without a manual conversion step.
    """

    model_config = ConfigDict(from_attributes=True)

    route_id: str | None
    trip_id: str | None
    vehicle_id: str | None
    arrival_time: datetime | None
    departure_time: datetime | None
    status: str | None

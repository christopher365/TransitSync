from pydantic import BaseModel, ConfigDict


class StopOut(BaseModel):
    """The wire format for one stop returned by the stop search endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    latitude: float
    longitude: float
    wheelchair_boarding: int

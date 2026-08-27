from pydantic import BaseModel, ConfigDict


class AlertOut(BaseModel):
    """The wire format for one active service alert."""

    model_config = ConfigDict(from_attributes=True)

    alert_id: str
    header: str
    effect: str | None
    severity: int | None
    cause: str | None

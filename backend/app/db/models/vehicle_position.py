from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VehiclePosition(Base):
    """One GPS position report for a vehicle, as polled from the MBTA API.

    Append-only by design: each poll inserts a new row rather than upserting
    a "current position" row. This keeps a full history (needed to actually
    measure the 10,000+ daily GPS coordinates ingestion target) and avoids a
    write-conflict story for concurrent pollers. Callers that only want the
    live position query for the latest row per vehicle/route instead of
    reading a mutable "current state" table.

    route_id is intentionally NOT a foreign key to `routes.id`: MBTA vehicle
    reports and route reference-data syncs happen on independent poll cycles,
    so a route referenced by a fresh vehicle report may not be in `routes`
    yet. A hard FK would make ingestion fail on ordering alone.
    """

    __tablename__ = "vehicle_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    route_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    trip_id: Mapped[str | None] = mapped_column(String, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    bearing: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    # MBTA's own vocabulary: "INCOMING_AT", "STOPPED_AT", "IN_TRANSIT_TO"
    current_status: Mapped[str] = mapped_column(String, nullable=False)
    # When MBTA says the position was recorded (source-of-truth timestamp).
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # When our ingestion pipeline wrote this row; drives staleness/throughput checks.
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

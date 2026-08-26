from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Stop(Base):
    """A cached transit stop, synced from the MBTA V3 API.

    Only reference data lives here — never live predictions. Predictions are
    fetched fresh on every request; see the data-access-layer discussion on
    why caching them would be actively misleading rather than just stale.
    """

    __tablename__ = "stops"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    # 0 = unknown, 1 = accessible, 2 = not accessible (MBTA's own encoding)
    wheelchair_boarding: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    routes: Mapped[list["Route"]] = relationship(
        secondary="stop_routes", back_populates="stops"
    )

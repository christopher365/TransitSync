from datetime import datetime, timezone

from sqlalchemy import DateTime, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Route(Base):
    """A cached transit route, synced from the MBTA V3 API."""

    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    short_name: Mapped[str] = mapped_column(String, nullable=False)
    long_name: Mapped[str] = mapped_column(String, nullable=False)
    # 0 light rail, 1 heavy rail, 2 commuter rail, 3 bus, 4 ferry (MBTA's own encoding)
    type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    stops: Mapped[list["Stop"]] = relationship(
        secondary="stop_routes", back_populates="routes"
    )

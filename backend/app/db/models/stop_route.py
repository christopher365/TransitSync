from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StopRoute(Base):
    """Junction table recording which routes serve which stops (many-to-many)."""

    __tablename__ = "stop_routes"

    stop_id: Mapped[str] = mapped_column(String, ForeignKey("stops.id"), primary_key=True)
    route_id: Mapped[str] = mapped_column(String, ForeignKey("routes.id"), primary_key=True)

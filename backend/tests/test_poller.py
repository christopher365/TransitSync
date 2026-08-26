import asyncio
from datetime import datetime, timezone

from app.db.models import VehiclePosition
from app.realtime.connection_manager import ConnectionManager
from app.realtime.poller import VehiclePoller


class FakeWebSocket:
    def __init__(self) -> None:
        self.sent_messages: list[dict] = []

    async def accept(self) -> None:
        pass

    async def send_json(self, data: dict) -> None:
        self.sent_messages.append(data)


def make_position(vehicle_id: str = "y1") -> VehiclePosition:
    now = datetime.now(timezone.utc)
    return VehiclePosition(
        vehicle_id=vehicle_id,
        route_id="Red",
        trip_id="trip-1",
        latitude=42.0,
        longitude=-71.0,
        bearing=1.0,
        speed=2.0,
        current_status="IN_TRANSIT_TO",
        updated_at=now,
        recorded_at=now,
    )


def test_run_cycle_broadcasts_every_position_poll_fn_returns() -> None:
    manager = ConnectionManager()
    websocket = FakeWebSocket()
    asyncio.run(manager.connect(websocket))
    poller = VehiclePoller(
        poll_fn=lambda: [make_position("y1"), make_position("y2")],
        connection_manager=manager,
    )

    asyncio.run(poller.run_cycle())

    assert len(websocket.sent_messages) == 2
    assert {m["vehicle_id"] for m in websocket.sent_messages} == {"y1", "y2"}


def test_run_cycle_broadcasts_nothing_when_poll_fn_returns_no_positions() -> None:
    manager = ConnectionManager()
    websocket = FakeWebSocket()
    asyncio.run(manager.connect(websocket))
    poller = VehiclePoller(poll_fn=lambda: [], connection_manager=manager)

    asyncio.run(poller.run_cycle())

    assert websocket.sent_messages == []


def test_run_cycle_swallows_poll_fn_exceptions_instead_of_raising() -> None:
    manager = ConnectionManager()

    def failing_poll() -> list[VehiclePosition]:
        raise RuntimeError("MBTA is down")

    poller = VehiclePoller(poll_fn=failing_poll, connection_manager=manager)

    asyncio.run(poller.run_cycle())  # should not raise

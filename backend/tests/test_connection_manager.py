import asyncio
from typing import Any

from app.realtime.connection_manager import ConnectionManager


class FakeWebSocket:
    """Stands in for a real WebSocket in tests: no network, just tracking."""

    def __init__(self, fail_on_send: bool = False) -> None:
        self.accepted = False
        self.sent_messages: list[Any] = []
        self._fail_on_send = fail_on_send

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: Any) -> None:
        if self._fail_on_send:
            raise RuntimeError("connection closed")
        self.sent_messages.append(data)


def test_connect_accepts_and_registers_the_websocket() -> None:
    manager = ConnectionManager()
    websocket = FakeWebSocket()

    asyncio.run(manager.connect(websocket))

    assert websocket.accepted is True
    assert manager.connection_count == 1


def test_broadcast_sends_to_every_connected_client() -> None:
    manager = ConnectionManager()
    first, second = FakeWebSocket(), FakeWebSocket()
    asyncio.run(manager.connect(first))
    asyncio.run(manager.connect(second))

    asyncio.run(manager.broadcast({"hello": "world"}))

    assert first.sent_messages == [{"hello": "world"}]
    assert second.sent_messages == [{"hello": "world"}]


def test_broadcast_drops_connections_that_fail_to_send() -> None:
    manager = ConnectionManager()
    healthy = FakeWebSocket()
    broken = FakeWebSocket(fail_on_send=True)
    asyncio.run(manager.connect(healthy))
    asyncio.run(manager.connect(broken))

    asyncio.run(manager.broadcast({"ping": True}))

    assert manager.connection_count == 1
    assert healthy.sent_messages == [{"ping": True}]


def test_disconnect_is_a_no_op_for_an_unknown_connection() -> None:
    manager = ConnectionManager()
    websocket = FakeWebSocket()

    manager.disconnect(websocket)  # should not raise

    assert manager.connection_count == 0

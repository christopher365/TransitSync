from typing import Any, Protocol


class SendsJson(Protocol):
    """The one WebSocket capability this class actually needs.

    Depending on this narrow Protocol instead of FastAPI's concrete
    WebSocket class means tests can hand in any object with a matching
    `send_json`/`accept` shape — no real network connection required.
    """

    async def accept(self) -> None: ...
    async def send_json(self, data: Any) -> None: ...


class ConnectionManager:
    """Tracks connected WebSocket clients and fans a message out to all of them."""

    def __init__(self) -> None:
        self._active_connections: list[SendsJson] = []

    async def connect(self, websocket: SendsJson) -> None:
        await websocket.accept()
        self._active_connections.append(websocket)

    def disconnect(self, websocket: SendsJson) -> None:
        if websocket in self._active_connections:
            self._active_connections.remove(websocket)

    @property
    def connection_count(self) -> int:
        return len(self._active_connections)

    async def broadcast(self, message: dict[str, Any]) -> None:
        stale_connections = []

        for connection in self._active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # The client is gone (closed tab, dropped network, etc.) —
                # note it for removal, but don't mutate the list mid-iteration.
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(connection)

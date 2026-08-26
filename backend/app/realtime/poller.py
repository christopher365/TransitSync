import asyncio
import logging
from collections.abc import Callable

from app.db.models import VehiclePosition
from app.realtime.connection_manager import ConnectionManager
from app.schemas.vehicle_position import VehiclePositionOut

logger = logging.getLogger(__name__)


class VehiclePoller:
    """Runs poll_fn on a fixed interval, forever, and broadcasts whatever it
    returns to every connected WebSocket client.

    Knows nothing about MBTA, HTTP, or the database — poll_fn is injected,
    so this class is testable with a plain stub function and stays correct
    even if the ingestion pipeline underneath it changes completely.
    """

    def __init__(
        self,
        poll_fn: Callable[[], list[VehiclePosition]],
        connection_manager: ConnectionManager,
        interval_seconds: float = 5.0,
    ) -> None:
        self._poll_fn = poll_fn
        self._connection_manager = connection_manager
        self._interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run_forever())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            self._task = None

    async def _run_forever(self) -> None:
        while True:
            await self.run_cycle()
            await asyncio.sleep(self._interval_seconds)

    async def run_cycle(self) -> None:
        """Runs exactly one poll-and-broadcast cycle.

        poll_fn does blocking work (an HTTP call, a database write), so it
        runs on a worker thread via asyncio.to_thread rather than directly
        on the event loop — otherwise every WebSocket client's connection
        would freeze for the duration of each poll.

        A poll failure (MBTA down, DB hiccup) is caught and logged rather
        than left to propagate: this loop runs forever in the background,
        and one bad cycle should never be allowed to kill it permanently.
        """
        try:
            positions = await asyncio.to_thread(self._poll_fn)
        except Exception:
            logger.exception("Vehicle poll failed; will retry next cycle")
            return

        for position in positions:
            payload = VehiclePositionOut.model_validate(position).model_dump(mode="json")
            await self._connection_manager.broadcast(payload)

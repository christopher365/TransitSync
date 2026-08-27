import time
from collections import defaultdict, deque


class RateLimiter:
    """A fixed-window rate limiter, keyed by client identifier (e.g. IP).

    Tracks recent request timestamps per key in memory. This is enough for
    a single-process deployment like this one; a multi-instance production
    deployment would need a shared store (e.g. Redis) instead, since this
    state doesn't survive a restart or get shared across processes.

    now is an explicit, injectable parameter (defaulting to the real clock)
    so tests can exercise window-expiry behavior without real sleeps.
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be a positive integer")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str, now: float | None = None) -> bool:
        now = now if now is not None else time.monotonic()
        timestamps = self._requests[key]

        while timestamps and now - timestamps[0] > self._window_seconds:
            timestamps.popleft()

        if len(timestamps) >= self._max_requests:
            return False

        timestamps.append(now)
        return True

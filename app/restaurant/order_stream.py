"""Live order status for the tracking page: server-sent events built from database polls.

The stream polls the database (not an in-process queue), so it also works when
several server processes run. The page falls back to plain polling if streaming
is blocked by a proxy (technical plan, section 7).
"""

import json
import time
from collections.abc import Callable, Iterator

from restaurant.constants import OrderStatus

KEEPALIVE_COMMENT = ": keepalive\n\n"


def format_event(name: str, payload: dict) -> str:
    """Return one server-sent event as text."""
    return f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


class OrderStatusStream:
    """Yields an event when the status first arrives and whenever it changes."""

    def __init__(
        self,
        read_status: Callable[[], OrderStatus],
        describe: Callable[[OrderStatus], dict],
        is_final: Callable[[OrderStatus], bool],
        poll_seconds: float,
        max_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Receive the readers and timers, so tests can run the stream without waiting."""
        self._read_status = read_status
        self._describe = describe
        self._is_final = is_final
        self._poll_seconds = poll_seconds
        self._max_seconds = max_seconds
        self._sleep = sleep
        self._clock = clock

    def events(self) -> Iterator[str]:
        """Yield events until the order is final or the time limit passes."""
        started = self._clock()
        status = self._read_status()
        yield format_event("status", self._describe(status))
        while not self._is_final(status) and self._clock() - started < self._max_seconds:
            self._sleep(self._poll_seconds)
            latest = self._read_status()
            if latest != status:
                status = latest
                yield format_event("status", self._describe(status))
            else:
                yield KEEPALIVE_COMMENT


class ChangeStream:
    """Yields a "board" event whenever the change marker differs from the last one seen.

    Used by the kitchen board: the page re-fetches the board on each event. The first
    frame is only a comment (the page was just rendered), so opening it never causes a refresh.
    """

    def __init__(
        self,
        read_marker: Callable[[], str],
        poll_seconds: float,
        max_seconds: float,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Receive the reader and timers, so tests can run the stream without waiting."""
        self._read_marker = read_marker
        self._poll_seconds = poll_seconds
        self._max_seconds = max_seconds
        self._sleep = sleep
        self._clock = clock

    def events(self) -> Iterator[str]:
        """Yield events until the time limit passes (the browser then reconnects)."""
        started = self._clock()
        marker = self._read_marker()
        yield KEEPALIVE_COMMENT
        while self._clock() - started < self._max_seconds:
            self._sleep(self._poll_seconds)
            latest = self._read_marker()
            if latest != marker:
                marker = latest
                yield format_event("board", {"marker": marker})
            else:
                yield KEEPALIVE_COMMENT

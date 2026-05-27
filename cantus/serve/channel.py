"""cantus.serve.channel — Channel Protocol + LocalMockReceiver.

The `Channel` Protocol defines a bidirectional message-passing contract that
external platform adapters (LINE / Telegram / Discord / Google Chat) will
implement in v0.4.2 / v0.4.3. cantus-serve-core ships exactly one concrete
implementation, `LocalMockReceiver`, used only as the ARCH-2 cross-capability
smoke-test load-bearer — it is in-process, in-memory, and intentionally not
suitable for any production transport.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from fastapi import FastAPI


@runtime_checkable
class Channel(Protocol):
    """Bidirectional channel contract — `receive()` + `send()`.

    A class conforms to this Protocol if it exposes both methods with the
    signatures below. cantus does not impose transport or platform semantics;
    concrete LINE / Telegram / Discord / Google Chat channels are scheduled
    for v0.4.2 / v0.4.3.
    """

    def receive(self) -> dict[str, Any]:
        """Return the next inbound message as a `dict`."""
        ...

    def send(self, message: dict[str, Any]) -> None:
        """Dispatch one outbound `dict` message."""
        ...


class LocalMockReceiver:
    """In-memory FIFO channel for ARCH-2 cross-capability smoke testing.

    `send(message)` appends to the right of an internal `collections.deque`;
    `receive()` pops from the left. Empty `receive()` raises `IndexError`
    with the literal substring "LocalMockReceiver queue is empty". Non-dict
    `send()` raises `TypeError` with the literal substring
    "LocalMockReceiver.send expects dict". The implementation never touches
    a network socket, file system, or process boundary.
    """

    def __init__(self) -> None:
        self._queue: deque[dict[str, Any]] = deque()

    def send(self, message: dict[str, Any]) -> None:
        if not isinstance(message, dict):
            raise TypeError(
                "LocalMockReceiver.send expects dict, "
                f"got {type(message).__name__}"
            )
        self._queue.append(message)

    def receive(self) -> dict[str, Any]:
        if not self._queue:
            raise IndexError("LocalMockReceiver queue is empty")
        return self._queue.popleft()


@runtime_checkable
class WebhookChannel(Channel, Protocol):
    """Channel that registers its own FastAPI route to receive inbound events.

    Extends :class:`Channel` with a single ``mount(app)`` method invoked by
    :func:`cantus.serve.serve` after Skill and dashboard routes are registered.
    LINE and Telegram webhook adapters implement this Protocol; in-process
    channels such as :class:`LocalMockReceiver` do not, and ``isinstance``
    correctly distinguishes the two so :func:`cantus.serve.serve` only calls
    ``mount`` on channels that require an HTTP entry point.
    """

    def mount(self, app: FastAPI) -> None:
        """Attach inbound routes to the FastAPI app."""
        ...


__all__ = ["Channel", "LocalMockReceiver", "WebhookChannel"]

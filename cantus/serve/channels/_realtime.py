"""cantus.serve.channels._realtime — Discord Gateway WebSocket client (v0.4.6).

Internal module wrapping a single Discord Gateway v10 JSON-encoded WebSocket
session for ``DiscordRealtimeChannel``. Public surface lives in
``cantus/serve/channels/discord.py``; nothing in this module is re-exported
from ``cantus.serve``.

Cross-platform wheel matrix: Linux x86_64 / macOS arm64+x86_64 / Windows AMD64
× CPython 3.10–3.13 all have prebuilt wheels for the ``websockets`` dependency
(pure-Python so no compile step) and the ``pynacl`` dependency consumed in
sibling ``_ed25519.py``. See ``pyproject.toml [project.optional-dependencies]
serve`` for the version pins.

The module deliberately omits any ``nacl`` import — Phase 3 of the B2 change
owns ``_ed25519.py`` independently and this client must remain importable
even before that phase lands.
"""

from __future__ import annotations

import asyncio
import json
import logging
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Final

import websockets
from websockets.asyncio.client import ClientConnection, connect

if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger("cantus.serve.channels")


class Opcode(IntEnum):
    """Discord Gateway v10 opcodes used by cantus.

    Only the opcodes cantus exchanges are listed; voice, presence-update, and
    request-guild-members are out of scope for the student echo-bot use case.
    """

    DISPATCH = 0
    HEARTBEAT = 1
    IDENTIFY = 2
    RESUME = 6
    RECONNECT = 7
    INVALID_SESSION = 9
    HELLO = 10
    HEARTBEAT_ACK = 11


_DEFAULT_GATEWAY_URL: Final[str] = "wss://gateway.discord.gg/?v=10&encoding=json"
_MAX_BACKOFF_SECONDS: Final[float] = 60.0
_DEFAULT_MAX_IDENTIFY_FAILURES: Final[int] = 10


class _IdentifyRejectedError(Exception):
    """Discord rejected our IDENTIFY (op 9 with d == False after op 2)."""


class _ResumableError(Exception):
    """Session dropped in a way that can be retried with backoff.

    Covers heartbeat ACK misses, ConnectionClosed mid-session, op 7
    RECONNECT requests, and op 9 d==True (Discord requesting we retry).
    """


class GatewayClient:
    """Discord Gateway v10 WebSocket client — one connection per cantus bot.

    Lifecycle:

    1. Caller awaits :meth:`start` from the FastAPI lifespan as a long-lived
       ``asyncio.Task``. ``start`` runs the reconnect loop forever, only
       returning when :meth:`stop` is called or 10 consecutive IDENTIFY
       rejections accumulate.
    2. Each session: TLS WebSocket connect → wait op 10 HELLO → start a
       heartbeat coroutine sending op 1 every ``heartbeat_interval`` ms →
       send op 6 RESUME (if session_id is known) or op 2 IDENTIFY → loop on
       received frames → dispatch op 0 events to ``on_event``.
    3. On disconnect: exponential backoff ``min(60, 2 ** attempts)`` seconds
       and reconnect. ``_session_id`` is preserved across reconnects so we
       attempt RESUME first; if Discord rejects with op 9 d==False we
       discard the session and try a fresh IDENTIFY on the *next* connect.

    The class is intentionally single-use (``start`` may not be called twice
    on the same instance) to mirror cantus' channel-instance-per-lifespan
    discipline.
    """

    def __init__(
        self,
        gateway_url: str = _DEFAULT_GATEWAY_URL,
        *,
        max_identify_failures: int = _DEFAULT_MAX_IDENTIFY_FAILURES,
    ) -> None:
        self._gateway_url = gateway_url
        self._max_identify_failures = max_identify_failures
        self._session_id: str | None = None
        self._seq: int | None = None
        self._stop_event = asyncio.Event()
        self._started = False
        self._ws: ClientConnection | None = None
        self._heartbeat_acked: bool = True
        self._heartbeat_interval_ms: float = 0.0
        self.last_error: BaseException | None = None

    # ----- public API ------------------------------------------------------

    async def start(
        self,
        *,
        bot_token: str,
        intents: int,
        on_event: Callable[[dict[str, Any]], None],
    ) -> None:
        """Run the reconnect loop until :meth:`stop` or 10 IDENTIFY failures.

        Does NOT raise out of the coroutine — if reconnect stops, ``last_error``
        is set and the coroutine returns cleanly. This is essential because
        the caller wraps ``start`` in ``asyncio.create_task`` from the FastAPI
        lifespan; a raised exception there would tear down the whole app.
        """

        if self._started:
            raise RuntimeError("GatewayClient.start() may only be called once")
        self._started = True

        attempts = 0
        identify_failures = 0

        while not self._stop_event.is_set():
            if attempts > 0:
                backoff = min(_MAX_BACKOFF_SECONDS, float(2 ** (attempts - 1)))
                await self._backoff_sleep(backoff)
                if self._stop_event.is_set():
                    return

            try:
                await self._run_one_session(
                    bot_token=bot_token,
                    intents=intents,
                    on_event=on_event,
                )
                # Clean session end (stop() or remote 1000 close) — reset.
                attempts = 0
                identify_failures = 0
            except _IdentifyRejectedError as exc:
                identify_failures += 1
                self.last_error = exc
                logger.warning(
                    "Discord Gateway IDENTIFY rejected (%d/%d)",
                    identify_failures,
                    self._max_identify_failures,
                )
                if identify_failures >= self._max_identify_failures:
                    logger.warning(
                        "Discord Gateway: %d consecutive IDENTIFY rejections — "
                        "stopping reconnect loop",
                        identify_failures,
                    )
                    return
                attempts += 1
            except _ResumableError as exc:
                self.last_error = exc
                logger.info("Discord Gateway resumable error: %s", exc)
                attempts += 1
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — defensive: never crash lifespan
                self.last_error = exc
                logger.warning("Discord Gateway unexpected error: %s", exc)
                attempts += 1

    async def _backoff_sleep(self, delay: float) -> None:
        """Reconnect-backoff wait.

        Exposed as a method so tests can monkeypatch a no-op replacement
        without leaking into the ``websockets`` library's internal
        ``asyncio.sleep`` calls (keep-alive ping interval, close timeout, …).
        """

        await asyncio.sleep(delay)

    async def stop(self) -> None:
        """Signal the reconnect loop to exit and close any open WebSocket."""

        self._stop_event.set()
        ws = self._ws
        if ws is not None:
            try:
                await ws.close(code=1000, reason="cantus shutdown")
            except Exception:  # noqa: BLE001 — close on shutdown is best-effort
                pass

    # ----- internals -------------------------------------------------------

    async def _run_one_session(
        self,
        *,
        bot_token: str,
        intents: int,
        on_event: Callable[[dict[str, Any]], None],
    ) -> None:
        """One WebSocket session — HELLO, IDENTIFY/RESUME, heartbeat, dispatch."""

        heartbeat_task: asyncio.Task[None] | None = None

        async with connect(self._gateway_url) as ws:
            self._ws = ws
            try:
                # First frame must be op 10 HELLO.
                hello_raw = await ws.recv()
                hello = _decode_frame(hello_raw)
                if hello.get("op") != Opcode.HELLO:
                    raise _ResumableError(
                        f"expected op 10 HELLO, got op {hello.get('op')}"
                    )
                self._heartbeat_interval_ms = float(hello["d"]["heartbeat_interval"])
                self._heartbeat_acked = True
                heartbeat_task = asyncio.create_task(self._heartbeat_loop(ws))

                # Decide RESUME vs fresh IDENTIFY.
                resuming = self._session_id is not None and self._seq is not None
                if resuming:
                    await _send_frame(
                        ws,
                        {
                            "op": Opcode.RESUME,
                            "d": {
                                "token": bot_token,
                                "session_id": self._session_id,
                                "seq": self._seq,
                            },
                        },
                    )
                else:
                    await _send_frame(
                        ws,
                        {
                            "op": Opcode.IDENTIFY,
                            "d": {
                                "token": bot_token,
                                "intents": intents,
                                "properties": {
                                    "$os": "linux",
                                    "$browser": "cantus",
                                    "$device": "cantus",
                                },
                            },
                        },
                    )

                # Frame loop.
                async for raw in ws:
                    frame = _decode_frame(raw)
                    op = frame.get("op")
                    if op == Opcode.DISPATCH:
                        # Update sequence cursor for future RESUME.
                        s = frame.get("s")
                        if isinstance(s, int):
                            self._seq = s
                        # Capture session_id from READY for future RESUMEs.
                        if frame.get("t") == "READY":
                            data = frame.get("d", {})
                            sid = data.get("session_id")
                            if isinstance(sid, str):
                                self._session_id = sid
                        try:
                            on_event(frame)
                        except Exception:  # noqa: BLE001 — caller bug; never crash loop
                            logger.exception(
                                "Discord Gateway on_event callback raised"
                            )
                    elif op == Opcode.HEARTBEAT_ACK:
                        self._heartbeat_acked = True
                    elif op == Opcode.HEARTBEAT:
                        # Discord requested an immediate heartbeat.
                        await _send_frame(
                            ws, {"op": Opcode.HEARTBEAT, "d": self._seq}
                        )
                    elif op == Opcode.RECONNECT:
                        # Discord told us to reconnect; keep session.
                        raise _ResumableError("server requested reconnect (op 7)")
                    elif op == Opcode.INVALID_SESSION:
                        # d == False → session unrecoverable, drop and re-IDENTIFY.
                        # d == True → may retry; treat as resumable.
                        d = frame.get("d")
                        if d is False:
                            if resuming:
                                # Drop session so the next attempt sends IDENTIFY.
                                self._session_id = None
                                self._seq = None
                                raise _ResumableError(
                                    "RESUME rejected, will re-IDENTIFY"
                                )
                            # We were trying a fresh IDENTIFY and got rejected.
                            raise _IdentifyRejectedError(
                                "IDENTIFY rejected by Discord (op 9 d=false)"
                            )
                        # d == True: retryable.
                        self._session_id = None
                        self._seq = None
                        raise _ResumableError("invalid session (retryable)")
                    # Other opcodes are unexpected from server — ignore.

                # Connection closed cleanly without an explicit signal.
                raise _ResumableError("WebSocket iterator exhausted")
            finally:
                if heartbeat_task is not None and not heartbeat_task.done():
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except (asyncio.CancelledError, Exception):  # noqa: BLE001
                        pass
                self._ws = None

    async def _heartbeat_loop(self, ws: ClientConnection) -> None:
        """Send op 1 every heartbeat_interval ms; close with 1011 on ACK miss."""

        interval_seconds = self._heartbeat_interval_ms / 1000.0
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                return
            if self._stop_event.is_set():
                return
            if not self._heartbeat_acked:
                # Previous heartbeat never got an ACK — connection is unhealthy.
                logger.warning(
                    "Discord Gateway heartbeat ACK missed; closing with 1011"
                )
                try:
                    await ws.close(code=1011, reason="heartbeat ack missed")
                except Exception:  # noqa: BLE001 — already closing, best-effort
                    pass
                return
            self._heartbeat_acked = False
            try:
                await _send_frame(ws, {"op": Opcode.HEARTBEAT, "d": self._seq})
            except (
                websockets.exceptions.ConnectionClosed,
                asyncio.CancelledError,
            ):
                return


# ----- frame helpers ---------------------------------------------------------


async def _send_frame(ws: ClientConnection, frame: dict[str, Any]) -> None:
    """JSON-encode and send a Gateway frame.

    Sending is funnelled through this helper so the IDENTIFY frame (which
    contains the bot token) is never str()-logged accidentally; we only log
    the opcode at debug level.
    """

    await ws.send(json.dumps(frame))
    logger.debug("Discord Gateway -> op %s", frame.get("op"))


def _decode_frame(raw: str | bytes) -> dict[str, Any]:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    parsed: Any = json.loads(raw)
    if not isinstance(parsed, dict):
        raise _ResumableError("non-object Gateway frame")
    return parsed


__all__ = [
    "GatewayClient",
    "Opcode",
]

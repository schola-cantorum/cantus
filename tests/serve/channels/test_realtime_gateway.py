"""Tests for cantus.serve.channels._realtime.GatewayClient.

The fake Discord Gateway is built on top of ``websockets.serve`` and driven
by per-test asyncio coroutines. Each test owns its server lifecycle so the
listener port is freed before the next test runs.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

import pytest
import websockets
from websockets.asyncio.server import ServerConnection, serve


# --- helpers -----------------------------------------------------------------


@asynccontextmanager
async def fake_gateway(
    handler: Callable[[ServerConnection], Awaitable[None]],
) -> AsyncIterator[str]:
    """Start a fake Discord Gateway server on a random local port.

    Yields the ``ws://`` URI the GatewayClient should be pointed at.
    """

    server = await serve(handler, host="127.0.0.1", port=0)
    sockets = server.sockets if hasattr(server, "sockets") else []
    if not sockets:
        # websockets 15/16 surfaces sockets via Server.server.sockets
        sockets = server.server.sockets  # type: ignore[attr-defined]
    port = sockets[0].getsockname()[1]
    try:
        yield f"ws://127.0.0.1:{port}"
    finally:
        server.close()
        await server.wait_closed()


async def _send_hello(ws: ServerConnection, heartbeat_interval: int = 45000) -> None:
    await ws.send(json.dumps({"op": 10, "d": {"heartbeat_interval": heartbeat_interval}}))


async def _send_ready(ws: ServerConnection, session_id: str = "sess1") -> None:
    await ws.send(
        json.dumps(
            {
                "op": 0,
                "t": "READY",
                "s": 1,
                "d": {
                    "session_id": session_id,
                    "resume_gateway_url": "wss://gateway.discord.gg/?v=10",
                    "user": {"id": "bot_id"},
                },
            }
        )
    )


# --- task 4.4: IDENTIFY flow -------------------------------------------------


@pytest.mark.anyio("asyncio")
async def test_identify_flow() -> None:
    """op10 HELLO -> op2 IDENTIFY -> op0 READY captures session_id."""
    from cantus.serve.channels._realtime import GatewayClient

    received_frames: list[dict[str, Any]] = []
    identify_seen = asyncio.Event()
    ready_sent = asyncio.Event()

    async def handler(ws: ServerConnection) -> None:
        await _send_hello(ws, heartbeat_interval=200)
        try:
            async for raw in ws:
                frame = json.loads(raw)
                received_frames.append(frame)
                if frame.get("op") == 2:
                    identify_seen.set()
                    await _send_ready(ws, session_id="sess_abc")
                    ready_sent.set()
                    # Stay open so client doesn't reconnect; close after a tick.
                    await asyncio.sleep(0.1)
                    await ws.close(code=1000)
                    return
        except websockets.exceptions.ConnectionClosed:
            return

    received_events: list[dict[str, Any]] = []

    def on_event(evt: dict[str, Any]) -> None:
        received_events.append(evt)

    async with fake_gateway(handler) as uri:
        client = GatewayClient(gateway_url=uri)
        task = asyncio.create_task(
            client.start(bot_token="bot_xyz", intents=0x9201, on_event=on_event)
        )
        try:
            await asyncio.wait_for(identify_seen.wait(), timeout=3.0)
            await asyncio.wait_for(ready_sent.wait(), timeout=3.0)
            # Let the READY event propagate and session_id store.
            await asyncio.sleep(0.05)
        finally:
            await client.stop()
            try:
                await asyncio.wait_for(task, timeout=3.0)
            except asyncio.TimeoutError:
                task.cancel()

    # The first IDENTIFY frame seen is op 2 with token + intents.
    identifies = [f for f in received_frames if f.get("op") == 2]
    assert len(identifies) == 1, f"expected 1 IDENTIFY, got {len(identifies)}"
    d = identifies[0]["d"]
    assert d["token"] == "bot_xyz"
    assert d["intents"] == 0x9201
    assert "properties" in d
    # Session captured from READY.
    assert client._session_id == "sess_abc"
    # READY event was dispatched to the callback.
    assert any(evt.get("t") == "READY" for evt in received_events)


# --- task 4.5: exponential backoff ------------------------------------------


@pytest.mark.anyio("asyncio")
async def test_exponential_backoff() -> None:
    """Three failed sessions in a row produce waits of [1, 2, 4] seconds."""
    from cantus.serve.channels import _realtime as realtime_mod
    from cantus.serve.channels._realtime import GatewayClient

    fail_count = 0
    max_fails = 3
    stop_after = asyncio.Event()

    async def handler(ws: ServerConnection) -> None:
        nonlocal fail_count
        await _send_hello(ws, heartbeat_interval=45000)
        try:
            async for raw in ws:
                frame = json.loads(raw)
                if frame.get("op") == 2:
                    # Close abruptly to simulate session failure (not an IDENTIFY
                    # rejection — exponential backoff is the topic here, not the
                    # 10-fail-stop, so use ConnectionClosed-style drop).
                    fail_count += 1
                    if fail_count >= max_fails:
                        stop_after.set()
                    await ws.close(code=1006)
                    return
        except websockets.exceptions.ConnectionClosed:
            return

    captured_sleeps: list[float] = []
    original_sleep = asyncio.sleep

    async def collecting_backoff_sleep(self: Any, delay: float) -> None:
        captured_sleeps.append(delay)
        # Skip the actual wait so the test finishes quickly.
        await original_sleep(0)

    async with fake_gateway(handler) as uri:
        # Patch GatewayClient._backoff_sleep so only reconnect waits are
        # captured; websockets internal asyncio.sleep stays untouched.
        original = realtime_mod.GatewayClient._backoff_sleep
        realtime_mod.GatewayClient._backoff_sleep = collecting_backoff_sleep  # type: ignore[assignment]
        try:
            client = GatewayClient(gateway_url=uri)
            task = asyncio.create_task(
                client.start(bot_token="t", intents=0, on_event=lambda e: None)
            )
            try:
                # Wait until we've seen at least three failed sessions.
                for _ in range(200):
                    if len(captured_sleeps) >= 3:
                        break
                    await original_sleep(0.05)
            finally:
                await client.stop()
                try:
                    await asyncio.wait_for(task, timeout=3.0)
                except asyncio.TimeoutError:
                    task.cancel()
        finally:
            realtime_mod.GatewayClient._backoff_sleep = original  # type: ignore[assignment]

    # First three reconnect waits should be 1, 2, 4 seconds.
    assert captured_sleeps[:3] == [1.0, 2.0, 4.0], f"got {captured_sleeps}"


# --- task 4.6: heartbeat ACK miss -------------------------------------------


@pytest.mark.anyio("asyncio")
async def test_heartbeat_ack_miss() -> None:
    """If server never ACKs heartbeat, client closes 1011 and reconnects."""
    from cantus.serve.channels._realtime import GatewayClient

    close_codes_seen: list[int | None] = []
    second_connect_seen = asyncio.Event()
    connections = 0

    async def handler(ws: ServerConnection) -> None:
        nonlocal connections
        connections += 1
        # Very short interval so the miss happens fast.
        await _send_hello(ws, heartbeat_interval=200)
        if connections == 1:
            try:
                async for raw in ws:
                    frame = json.loads(raw)
                    if frame.get("op") == 2:
                        # ack IDENTIFY with READY
                        await _send_ready(ws, session_id="sess_hb")
                    # Intentionally do NOT respond to op 1 HEARTBEAT.
            except websockets.exceptions.ConnectionClosed as exc:
                close_codes_seen.append(exc.code)
        else:
            second_connect_seen.set()
            # On second connect just close to end the test quickly.
            await asyncio.sleep(0.05)
            await ws.close(code=1000)

    async with fake_gateway(handler) as uri:
        client = GatewayClient(gateway_url=uri)
        task = asyncio.create_task(
            client.start(bot_token="t", intents=0, on_event=lambda e: None)
        )
        try:
            await asyncio.wait_for(second_connect_seen.wait(), timeout=5.0)
        finally:
            await client.stop()
            try:
                await asyncio.wait_for(task, timeout=3.0)
            except asyncio.TimeoutError:
                task.cancel()

    # Verify the first session closed with 1011 (server's view of client close).
    assert 1011 in close_codes_seen, f"close codes seen: {close_codes_seen}"


# --- task 4.2 verify: RESUME falls back to IDENTIFY ------------------------


@pytest.mark.anyio("asyncio")
async def test_resume_fallback_to_identify() -> None:
    """When server returns op9 d=false to a RESUME, next connection sends IDENTIFY."""
    from cantus.serve.channels._realtime import GatewayClient

    connection_idx = 0
    second_connect_op2 = asyncio.Event()
    second_op2_frame: dict[str, Any] | None = None

    async def handler(ws: ServerConnection) -> None:
        nonlocal connection_idx, second_op2_frame
        connection_idx += 1
        await _send_hello(ws, heartbeat_interval=45000)
        try:
            async for raw in ws:
                frame = json.loads(raw)
                if connection_idx == 1:
                    # First connection: ack IDENTIFY with READY then drop.
                    if frame.get("op") == 2:
                        await _send_ready(ws, session_id="will_be_invalid")
                        await asyncio.sleep(0.05)
                        await ws.close(code=1006)
                        return
                elif connection_idx == 2:
                    # Second connection: client should try RESUME (op 6).
                    if frame.get("op") == 6:
                        await ws.send(json.dumps({"op": 9, "d": False}))
                        await asyncio.sleep(0.05)
                        await ws.close(code=1000)
                        return
                    elif frame.get("op") == 2:
                        # If RESUME wasn't tried, fail the assert via empty frame.
                        await ws.close(code=1000)
                        return
                else:
                    # Third connection: should be a FRESH IDENTIFY (op 2 with
                    # no session_id because we threw it away).
                    if frame.get("op") == 2:
                        second_op2_frame = frame
                        second_connect_op2.set()
                        await ws.close(code=1000)
                        return
                    elif frame.get("op") == 6:
                        # Client shouldn't try RESUME after invalid-session.
                        await ws.close(code=1000)
                        return
        except websockets.exceptions.ConnectionClosed:
            return

    async with fake_gateway(handler) as uri:
        client = GatewayClient(gateway_url=uri)
        task = asyncio.create_task(
            client.start(bot_token="bot_t", intents=0x1, on_event=lambda e: None)
        )
        try:
            await asyncio.wait_for(second_connect_op2.wait(), timeout=8.0)
        finally:
            await client.stop()
            try:
                await asyncio.wait_for(task, timeout=3.0)
            except asyncio.TimeoutError:
                task.cancel()

    assert second_op2_frame is not None
    assert second_op2_frame["op"] == 2
    assert second_op2_frame["d"]["token"] == "bot_t"
    # Critically the client cleared session_id before this IDENTIFY.
    assert client._session_id is None


# --- task 4.3: 10 IDENTIFY failures stop without raise ----------------------


@pytest.mark.anyio("asyncio")
async def test_ten_failures_stop_without_raise() -> None:
    """Server op9 d=false to every IDENTIFY -> start() returns cleanly."""
    from cantus.serve.channels import _realtime as realtime_mod
    from cantus.serve.channels._realtime import GatewayClient, _IdentifyRejectedError

    identify_attempts = 0

    async def handler(ws: ServerConnection) -> None:
        nonlocal identify_attempts
        await _send_hello(ws, heartbeat_interval=45000)
        try:
            async for raw in ws:
                frame = json.loads(raw)
                if frame.get("op") == 2:
                    identify_attempts += 1
                    await ws.send(json.dumps({"op": 9, "d": False}))
                    await asyncio.sleep(0.02)
                    await ws.close(code=1000)
                    return
        except websockets.exceptions.ConnectionClosed:
            return

    # Patch backoff sleep so the test is fast (don't touch websockets internals).
    original = realtime_mod.GatewayClient._backoff_sleep

    async def fast_backoff(self: Any, delay: float) -> None:
        return None

    realtime_mod.GatewayClient._backoff_sleep = fast_backoff  # type: ignore[assignment]
    try:
        async with fake_gateway(handler) as uri:
            client = GatewayClient(gateway_url=uri)
            # start() must return cleanly — no raise.
            await asyncio.wait_for(
                client.start(
                    bot_token="bad_token", intents=0, on_event=lambda e: None
                ),
                timeout=15.0,
            )
    finally:
        realtime_mod.GatewayClient._backoff_sleep = original  # type: ignore[assignment]

    assert identify_attempts == 10, f"expected 10 attempts, saw {identify_attempts}"
    assert isinstance(client.last_error, _IdentifyRejectedError)


# --- Gate B M2: HELLO heartbeat_interval bounds check -----------------------


@pytest.mark.parametrize(
    "bad_interval",
    [0, 99, 120001, 200000],
    ids=["zero", "below_lower_bound", "above_upper_bound", "far_above_upper_bound"],
)
@pytest.mark.anyio("asyncio")
async def test_hello_heartbeat_interval_out_of_bounds_triggers_resumable(
    bad_interval: int,
) -> None:
    """HELLO with heartbeat_interval outside [100, 120000] → no HEARTBEAT, reconnect."""
    from cantus.serve.channels import _realtime as realtime_mod
    from cantus.serve.channels._realtime import GatewayClient, _ResumableError

    heartbeat_seen: list[int] = []
    backoff_count = 0

    async def handler(ws: ServerConnection) -> None:
        await _send_hello(ws, heartbeat_interval=bad_interval)
        try:
            async for raw in ws:
                frame = json.loads(raw)
                if frame.get("op") == 1:
                    heartbeat_seen.append(frame.get("op"))
        except websockets.exceptions.ConnectionClosed:
            return

    original_backoff = realtime_mod.GatewayClient._backoff_sleep

    async def short_backoff(self: Any, delay: float) -> None:
        nonlocal backoff_count
        backoff_count += 1
        await asyncio.sleep(0)

    realtime_mod.GatewayClient._backoff_sleep = short_backoff  # type: ignore[assignment]
    client: Any = None
    backoff_observed_before_stop = False
    try:
        async with fake_gateway(handler) as uri:
            client = GatewayClient(gateway_url=uri)
            task = asyncio.create_task(
                client.start(bot_token="t", intents=0, on_event=lambda e: None)
            )
            try:
                # Validation must trigger backoff well before any heartbeat
                # could fire, even for bad_interval=200000 (200s).
                for _ in range(60):
                    if backoff_count >= 1:
                        backoff_observed_before_stop = True
                        break
                    await asyncio.sleep(0.05)
            finally:
                await client.stop()
                try:
                    await asyncio.wait_for(task, timeout=3.0)
                except asyncio.TimeoutError:
                    task.cancel()
    finally:
        realtime_mod.GatewayClient._backoff_sleep = original_backoff  # type: ignore[assignment]

    assert backoff_observed_before_stop, (
        f"validation did not trigger backoff for bad interval {bad_interval} "
        "within the polling window"
    )
    assert not heartbeat_seen, (
        f"unexpected HEARTBEAT sent for bad interval {bad_interval}"
    )
    assert isinstance(client.last_error, _ResumableError)


@pytest.mark.anyio("asyncio")
async def test_hello_heartbeat_interval_at_lower_bound_is_accepted() -> None:
    """heartbeat_interval=100 is accepted (boundary case)."""
    from cantus.serve.channels._realtime import GatewayClient

    identify_seen = asyncio.Event()

    async def handler(ws: ServerConnection) -> None:
        await _send_hello(ws, heartbeat_interval=100)
        try:
            async for raw in ws:
                frame = json.loads(raw)
                if frame.get("op") == 2:
                    identify_seen.set()
                    await ws.close(code=1000)
                    return
        except websockets.exceptions.ConnectionClosed:
            return

    async with fake_gateway(handler) as uri:
        client = GatewayClient(gateway_url=uri)
        task = asyncio.create_task(
            client.start(bot_token="t", intents=0, on_event=lambda e: None)
        )
        try:
            await asyncio.wait_for(identify_seen.wait(), timeout=3.0)
        finally:
            await client.stop()
            try:
                await asyncio.wait_for(task, timeout=3.0)
            except asyncio.TimeoutError:
                task.cancel()


# --- Gate B M3: seq only advances on DISPATCH frames via helper -------------


@pytest.mark.anyio("asyncio")
async def test_accept_dispatch_frame_advances_seq_when_s_is_int() -> None:
    """DISPATCH frame with integer s advances self._seq via the helper."""
    from cantus.serve.channels._realtime import GatewayClient

    client = GatewayClient()
    client._seq = 42
    events: list[dict[str, Any]] = []
    frame = {"op": 0, "s": 43, "t": "MESSAGE_CREATE", "d": {"x": 1}}

    client._accept_dispatch_frame(frame, events.append)

    assert client._seq == 43
    assert events == [frame]


@pytest.mark.anyio("asyncio")
async def test_accept_dispatch_frame_does_not_advance_seq_when_s_is_missing() -> None:
    """DISPATCH frame missing s leaves self._seq untouched."""
    from cantus.serve.channels._realtime import GatewayClient

    client = GatewayClient()
    client._seq = 42
    client._accept_dispatch_frame(
        {"op": 0, "t": "MESSAGE_CREATE", "d": {}}, lambda f: None
    )
    assert client._seq == 42


@pytest.mark.anyio("asyncio")
async def test_accept_dispatch_frame_captures_ready_session_id() -> None:
    """DISPATCH READY frame stores session_id for future RESUME."""
    from cantus.serve.channels._realtime import GatewayClient

    client = GatewayClient()
    client._accept_dispatch_frame(
        {
            "op": 0,
            "s": 1,
            "t": "READY",
            "d": {"session_id": "sess_capture_test"},
        },
        lambda f: None,
    )
    assert client._session_id == "sess_capture_test"


@pytest.mark.anyio("asyncio")
async def test_seq_only_advances_on_dispatch_in_frame_loop() -> None:
    """Non-DISPATCH frame carrying integer s does NOT advance self._seq."""
    from cantus.serve.channels._realtime import GatewayClient

    seq_observed_via_heartbeat: list[Any] = []
    accept_dispatch_calls: list[dict[str, Any]] = []

    async def handler(ws: ServerConnection) -> None:
        await _send_hello(ws, heartbeat_interval=200)
        try:
            async for raw in ws:
                frame = json.loads(raw)
                if frame.get("op") == 2:
                    # Send a non-DISPATCH frame with integer s — must NOT
                    # advance seq.
                    await ws.send(
                        json.dumps({"op": 11, "s": 999, "d": None})
                    )
                    # Send a real DISPATCH frame that should advance seq.
                    await ws.send(
                        json.dumps(
                            {
                                "op": 0,
                                "s": 43,
                                "t": "MESSAGE_CREATE",
                                "d": {"channel_id": "c1"},
                            }
                        )
                    )
                    # Request a heartbeat so client sends one back with current
                    # seq — that lets us observe the seq value over the wire.
                    await ws.send(json.dumps({"op": 1, "d": None}))
                if frame.get("op") == 1:
                    seq_observed_via_heartbeat.append(frame.get("d"))
                    await ws.close(code=1000)
                    return
        except websockets.exceptions.ConnectionClosed:
            return

    async with fake_gateway(handler) as uri:
        from cantus.serve.channels._realtime import GatewayClient as _GC

        original_accept = _GC._accept_dispatch_frame

        def spy(
            self: Any, frame: dict[str, Any], on_event: Any
        ) -> None:
            accept_dispatch_calls.append(frame)
            return original_accept(self, frame, on_event)

        _GC._accept_dispatch_frame = spy  # type: ignore[assignment]
        try:
            client = GatewayClient(gateway_url=uri)
            task = asyncio.create_task(
                client.start(bot_token="t", intents=0, on_event=lambda e: None)
            )
            try:
                for _ in range(60):
                    if seq_observed_via_heartbeat:
                        break
                    await asyncio.sleep(0.05)
            finally:
                await client.stop()
                try:
                    await asyncio.wait_for(task, timeout=3.0)
                except asyncio.TimeoutError:
                    task.cancel()
        finally:
            _GC._accept_dispatch_frame = original_accept  # type: ignore[assignment]

    # Helper invoked exactly once — for the DISPATCH frame only.
    assert len(accept_dispatch_calls) == 1
    assert accept_dispatch_calls[0]["op"] == 0
    assert accept_dispatch_calls[0]["s"] == 43
    # seq advanced to DISPATCH's s, NOT to the HEARTBEAT_ACK's s=999.
    assert client._seq == 43
    # heartbeat payload carried the advanced seq.
    assert seq_observed_via_heartbeat[0] == 43

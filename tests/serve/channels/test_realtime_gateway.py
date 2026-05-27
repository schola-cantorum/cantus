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
        await _send_hello(ws, heartbeat_interval=80)
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

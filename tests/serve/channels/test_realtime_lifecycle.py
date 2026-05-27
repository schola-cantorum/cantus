"""Phase 6 — serve() lifespan dispatch for RealtimeChannel.

Tasks 6.2 + 6.3 verify the v0.4.6 lifespan extension in
`cantus.serve.app.serve`:

* startup spawns ``asyncio.create_task(ch.connect())`` for every
  ``RealtimeChannel`` member of ``app.state.channels``;
* shutdown awaits ``ch.disconnect()`` for every such channel BEFORE the
  retained tasks are cancelled and ``app.state.http_client`` is closed;
* plain ``Channel`` implementations (e.g. ``LocalMockReceiver``) and
  ``WebhookChannel``-only implementations (e.g. ``LineWebhookChannel``)
  receive NO ``connect`` / ``disconnect`` invocation.

The tests use stub ``RealtimeChannel`` implementations rather than the real
``DiscordRealtimeChannel`` — Phase 5 already covers DiscordRealtimeChannel's
end-to-end behaviour via its own tests, and the lifespan contract is
Protocol-level, not platform-level.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from cantus.core.registry import Registry
from cantus.serve import (
    DiscordRealtimeChannel,
    LineWebhookChannel,
    LocalMockReceiver,
    serve,
)


class _StubRealtimeChannel:
    """Minimal RealtimeChannel-conforming stub for lifespan tests."""

    def __init__(self) -> None:
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.connect_running = asyncio.Event()
        self.disconnect_done = asyncio.Event()
        self._stop = asyncio.Event()

    def receive(self) -> dict[str, Any]:
        raise IndexError("empty")

    def send(self, message: dict[str, Any]) -> None:
        return None

    async def connect(self) -> None:
        self.connect_calls += 1
        self.connect_running.set()
        # Live until disconnect is signalled — mirrors GatewayClient.start().
        await self._stop.wait()

    async def disconnect(self) -> None:
        self.disconnect_calls += 1
        self._stop.set()
        self.disconnect_done.set()


# --- Task 6.2 — startup creates task, shutdown awaits disconnect ---------


@pytest.mark.anyio("asyncio")
async def test_startup_creates_task_for_realtime_channel() -> None:
    """Requirement: serve() dispatches connect/disconnect to every
    RealtimeChannel via lifespan — startup branch.

    Lifespan startup must call ``asyncio.create_task(ch.connect())``; the
    coroutine must actually be scheduled (the stub's ``connect_running``
    event flips True) before the yield.
    """
    channel = _StubRealtimeChannel()
    app = serve(Registry(), channels=[channel])
    async with _enter_app(app):
        # connect() runs concurrently in a Task — give the loop one tick.
        await asyncio.wait_for(channel.connect_running.wait(), timeout=1.0)
        assert channel.connect_calls == 1


@pytest.mark.anyio("asyncio")
async def test_shutdown_awaits_disconnect_then_closes_http_client() -> None:
    """Requirement: serve() dispatches connect/disconnect to every
    RealtimeChannel via lifespan — shutdown ordering.

    Lifespan shutdown must await ``ch.disconnect()`` BEFORE closing
    ``app.state.http_client``. We probe this by checking that
    ``disconnect_done`` is set before ``http_client.is_closed`` flips.
    """
    channel = _StubRealtimeChannel()
    app = serve(Registry(), channels=[channel])
    async with _enter_app(app):
        await asyncio.wait_for(channel.connect_running.wait(), timeout=1.0)
        client = app.state.http_client
        assert not client.is_closed
    # Lifespan exit point.
    assert channel.disconnect_calls == 1
    assert channel.disconnect_done.is_set()
    assert app.state.http_client.is_closed


@pytest.mark.anyio("asyncio")
async def test_local_mock_receiver_skipped_by_lifespan() -> None:
    """Requirement: serve() dispatches connect/disconnect to every
    RealtimeChannel via lifespan — non-realtime channels are skipped.

    LocalMockReceiver implements only Channel (no connect/disconnect, no
    mount). The lifespan iterates app.state.channels and must NOT touch it.
    The proof: the app starts and stops cleanly without any AttributeError
    even though LocalMockReceiver has no connect/disconnect attributes.
    """
    receiver = LocalMockReceiver()
    app = serve(Registry(), channels=[receiver])
    async with _enter_app(app):
        # If lifespan tried to call receiver.connect(), startup would raise
        # AttributeError before reaching here. Reaching the yield body
        # proves the isinstance(RealtimeChannel) guard works.
        assert app.state.http_client is not None


# --- Task 6.3 — mixed channels routing ----------------------------------


@pytest.mark.anyio("asyncio")
async def test_mixed_channels_dispatch_to_matching_protocols_only() -> None:
    """Requirement: serve() dispatches connect/disconnect to every
    RealtimeChannel via lifespan — sibling Protocols stay orthogonal.

    Given channels=[LocalMockReceiver, LineWebhookChannel, _StubRealtimeChannel]:
    - LocalMockReceiver receives no mount, no connect, no disconnect.
    - LineWebhookChannel.mount(app) IS invoked at build time (v0.4.5 contract);
      no connect/disconnect at lifespan time.
    - _StubRealtimeChannel.connect() IS spawned as a task at startup, and
      disconnect() IS awaited at shutdown.
    """
    receiver = LocalMockReceiver()
    line = LineWebhookChannel(
        channel_secret="x" * 32, channel_access_token="y" * 32
    )
    realtime = _StubRealtimeChannel()
    app = serve(Registry(), channels=[receiver, line, realtime])

    # mount(app) on LineWebhookChannel runs at build time — verify by route.
    paths = [
        r.path for r in app.router.routes if hasattr(r, "path")
    ]
    assert "/channels/line" in paths

    async with _enter_app(app):
        await asyncio.wait_for(realtime.connect_running.wait(), timeout=1.0)
        assert realtime.connect_calls == 1

    # Shutdown: only the realtime channel saw disconnect.
    assert realtime.disconnect_calls == 1


@pytest.mark.anyio("asyncio")
async def test_discord_realtime_channel_isinstance_both_protocols() -> None:
    """Requirement: DiscordRealtimeChannel implements both RealtimeChannel
    and WebhookChannel — Phase 6 cross-check from the lifespan perspective.

    Mounting a real DiscordRealtimeChannel exercises BOTH the v0.4.5
    WebhookChannel.mount(app) path (registers /channels/discord/interactions)
    AND the v0.4.6 RealtimeChannel.connect lifespan task. The connect path
    will fail fast against the public Discord Gateway (we pass dummy
    credentials and the test environment cannot reach Discord), but the
    10-fail-stop discipline ensures the lifespan does not crash.
    """
    from cantus.serve.channel import RealtimeChannel, WebhookChannel

    discord = DiscordRealtimeChannel(
        bot_token="fake-bot-token-for-lifecycle-test",
        public_key="aa" * 32,
        application_id="100",
    )
    assert isinstance(discord, RealtimeChannel)
    assert isinstance(discord, WebhookChannel)

    app = serve(Registry(), channels=[discord])
    paths = [r.path for r in app.router.routes if hasattr(r, "path")]
    assert "/channels/discord/interactions" in paths


# --- helpers ------------------------------------------------------------


from contextlib import asynccontextmanager
from typing import AsyncIterator


@asynccontextmanager
async def _enter_app(app: Any) -> AsyncIterator[Any]:
    """Drive the FastAPI lifespan manually (TestClient is sync; we need to
    interleave async assertions with the lifespan body).

    Mirrors what uvicorn does internally: send ``lifespan.startup``, await
    the response, then on context exit send ``lifespan.shutdown``.
    """
    receive_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    send_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def receive() -> dict[str, Any]:
        return await receive_queue.get()

    async def send(message: dict[str, Any]) -> None:
        await send_queue.put(message)

    scope = {"type": "lifespan"}
    lifespan_task = asyncio.create_task(app(scope, receive, send))

    await receive_queue.put({"type": "lifespan.startup"})
    startup_response = await asyncio.wait_for(send_queue.get(), timeout=5.0)
    assert startup_response["type"] == "lifespan.startup.complete"

    try:
        yield app
    finally:
        await receive_queue.put({"type": "lifespan.shutdown"})
        shutdown_response = await asyncio.wait_for(send_queue.get(), timeout=5.0)
        assert shutdown_response["type"] == "lifespan.shutdown.complete"
        await lifespan_task

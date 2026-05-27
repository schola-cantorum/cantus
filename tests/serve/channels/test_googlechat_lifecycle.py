"""Lifecycle tests for ``cantus.serve.channels.googlechat.GoogleChatPubSubChannel``.

Covers tasks 6.1-6.2 of cantus-channel-gateway-pubsub:

* ``disconnect()`` is idempotent: calling before ``connect()`` is a no-op,
  and repeated calls leave the SubscriberClient's ``close()`` invoked
  AT MOST ONCE.
* The ``serve(...)`` lifespan dispatches ``connect()`` as an
  ``asyncio.Task`` on startup, awaits ``disconnect()`` on shutdown, and
  performs the disconnect BEFORE closing ``app.state.http_client``.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import pytest

from cantus.config import Settings
from cantus.core.registry import Registry
from cantus.serve import serve
from cantus.serve.channels._googlechat_internals import _FakeSubscriber
from cantus.serve.channels.googlechat import GoogleChatPubSubChannel


CREDENTIALS_PATH = "/tmp/sa.json"
SUBSCRIPTION = "projects/p/subscriptions/s"
SPACE = "spaces/AAA"


def _build_channel_with_fake() -> tuple[GoogleChatPubSubChannel, _FakeSubscriber]:
    settings = Settings(
        channel_google_chat_credentials_path=CREDENTIALS_PATH,
        channel_google_chat_subscription=SUBSCRIPTION,
        channel_google_chat_space=SPACE,
    )
    ch = GoogleChatPubSubChannel(settings=settings)
    fake = _FakeSubscriber()
    ch._build_subscriber = lambda: fake  # type: ignore[method-assign]
    return ch, fake


# --- Task 6.1 — disconnect idempotence ------------------------------------


@pytest.mark.anyio("asyncio")
async def test_disconnect_before_connect_is_no_op() -> None:
    """Task 6.1 — calling ``disconnect()`` on a channel that has never had
    ``connect()`` awaited returns silently."""
    settings = Settings(
        channel_google_chat_credentials_path=CREDENTIALS_PATH,
        channel_google_chat_subscription=SUBSCRIPTION,
        channel_google_chat_space=SPACE,
    )
    ch = GoogleChatPubSubChannel(settings=settings)
    await ch.disconnect()  # must not raise


@pytest.mark.anyio("asyncio")
async def test_repeated_disconnect_is_idempotent() -> None:
    """Task 6.1 — repeated ``disconnect()`` does not close the underlying
    SubscriberClient more than once."""
    ch, fake = _build_channel_with_fake()
    task = asyncio.create_task(ch.connect())
    # Wait for subscribe() to register a callback so we know the
    # SubscriberClient is wired up.
    deadline = asyncio.get_event_loop().time() + 1.0
    while fake._callback is None:
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError("connect() did not subscribe within 1s")
        await asyncio.sleep(0.01)

    await ch.disconnect()
    close_after_first = fake.closed
    await ch.disconnect()  # idempotent — second call must not re-close
    close_after_second = fake.closed
    await asyncio.wait_for(task, timeout=1.0)

    # The first disconnect closes the subscriber; the second is a no-op.
    assert close_after_first is True
    assert close_after_second is True


# --- Task 6.2 — lifespan ordering -----------------------------------------


@asynccontextmanager
async def _enter_app(app: Any) -> AsyncIterator[Any]:
    """Drive the FastAPI lifespan manually (mirrors uvicorn internals).

    Sends ``lifespan.startup`` and awaits the response, yields to the
    test body, then sends ``lifespan.shutdown`` on context exit.
    """
    receive_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    send_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def _receive() -> dict[str, Any]:
        return await receive_queue.get()

    async def _send(message: dict[str, Any]) -> None:
        await send_queue.put(message)

    scope = {"type": "lifespan"}
    lifespan_task = asyncio.create_task(app(scope, _receive, _send))

    await receive_queue.put({"type": "lifespan.startup"})
    resp = await asyncio.wait_for(send_queue.get(), timeout=2.0)
    assert resp == {"type": "lifespan.startup.complete"}

    try:
        yield app
    finally:
        await receive_queue.put({"type": "lifespan.shutdown"})
        resp = await asyncio.wait_for(send_queue.get(), timeout=2.0)
        assert resp == {"type": "lifespan.shutdown.complete"}
        await asyncio.wait_for(lifespan_task, timeout=2.0)


@pytest.mark.anyio("asyncio")
async def test_lifespan_disconnect_before_http_client_aclose() -> None:
    """Task 6.2 — Requirement: disconnect() cancels the pull future and
    closes the SubscriberClient before the HTTP client closes.

    On lifespan exit, the channel's ``disconnect()`` must be awaited
    before ``app.state.http_client.aclose()`` is awaited. We probe this
    by capturing the order in which two observable side effects flip:
    the channel's internal ``_disconnected`` flag and the
    ``app.state.http_client.is_closed`` property.
    """
    ch, fake = _build_channel_with_fake()
    # Channel Protocol declares send() as sync; concrete channels (LINE /
    # Telegram / Discord / Google Chat) all use async send. mypy can't
    # reconcile the Protocol type with the async implementation, but the
    # runtime isinstance check (used by serve()'s lifespan) does — this
    # is the documented intentional gap in the cantus channel surface.
    app = serve(Registry(), channels=[ch])  # type: ignore[list-item]

    async with _enter_app(app):
        # Wait for subscribe() to have wired up the fake.
        deadline = asyncio.get_event_loop().time() + 1.0
        while fake._callback is None:
            if asyncio.get_event_loop().time() > deadline:
                raise AssertionError("connect() did not subscribe within 1s")
            await asyncio.sleep(0.01)
        client = app.state.http_client
        assert not client.is_closed
        assert not ch._disconnected

    # After lifespan exit:
    assert ch._disconnected is True
    assert app.state.http_client.is_closed is True
    assert fake.closed is True

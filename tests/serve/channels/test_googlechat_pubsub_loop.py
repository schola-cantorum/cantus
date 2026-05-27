"""Tests for the Pub/Sub pull loop inside
``cantus.serve.channels.googlechat.GoogleChatPubSubChannel``.

Covers tasks 5.1-5.6 of cantus-channel-gateway-pubsub:

* The bundled ``_FakeSubscriber`` test helper drives the channel callback.
* A delivered, well-formed message is enqueued THEN acked.
* Malformed JSON is nacked, the queue is unchanged, and the callback
  swallows the parse error so the SubscriberClient stays running.
* Streaming-pull failures back off via ``min(60, 2**attempts)`` and the
  recorded sleep schedule for the first three failures is ``[1, 2, 4]``.
* Ten consecutive failures set ``last_error`` and exit the ``connect()``
  coroutine cleanly (no raise out to the lifespan task).
* ``message.ack()`` is invoked only AFTER the successful enqueue — a
  queue-append failure must leave the message unacked so Pub/Sub
  re-delivers it.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from cantus.config import Settings
from cantus.serve.channels._googlechat_internals import _FakeSubscriber
from cantus.serve.channels.googlechat import GoogleChatPubSubChannel


# Stand-in inputs — none of these touch a real GCP project.
CREDENTIALS_PATH = "/tmp/sa.json"
SUBSCRIPTION = "projects/p/subscriptions/s"
SPACE = "spaces/AAA"


def _build_channel() -> tuple[GoogleChatPubSubChannel, _FakeSubscriber]:
    """Construct a channel and return it together with a fake subscriber.

    The fake is wired into the channel via ``_build_subscriber`` patching
    so ``connect()`` uses the in-memory transport instead of the real
    ``SubscriberClient``.
    """
    settings = Settings(
        channel_google_chat_credentials_path=CREDENTIALS_PATH,
        channel_google_chat_subscription=SUBSCRIPTION,
        channel_google_chat_space=SPACE,
    )
    ch = GoogleChatPubSubChannel(settings=settings)
    fake = _FakeSubscriber()
    ch._build_subscriber = lambda: fake  # type: ignore[method-assign]
    return ch, fake


async def _wait_until(predicate: Any, timeout: float = 1.0) -> None:
    """Pump the event loop until ``predicate()`` is True (or timeout)."""
    deadline = asyncio.get_event_loop().time() + timeout
    while not predicate():
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError(f"predicate did not become True within {timeout}s")
        await asyncio.sleep(0.01)


# --- Task 5.1 — _FakeSubscriber helper ------------------------------------


@pytest.mark.anyio("asyncio")
async def test_fake_subscriber_pushes_message_to_callback() -> None:
    """Task 5.1 — the _FakeSubscriber helper drives the registered callback."""
    received: list[Any] = []
    fake = _FakeSubscriber()
    fake.subscribe("projects/x/subscriptions/y", callback=received.append)
    msg = fake.push_message(b'{"event":"test"}')
    assert len(received) == 1
    assert received[0] is msg
    assert msg.data == b'{"event":"test"}'


# --- Task 5.2 — message enqueued then acked -------------------------------


@pytest.mark.anyio("asyncio")
async def test_message_enqueued_then_acked() -> None:
    """Task 5.2 — Requirement: connect() opens a Pub/Sub streaming pull,
    acks after enqueue, and applies exponential backoff with a ten-failure
    ceiling — well-formed event lands in queue then gets acked."""
    ch, fake = _build_channel()
    task = asyncio.create_task(ch.connect())
    try:
        await _wait_until(lambda: fake._callback is not None)
        msg = fake.push_message(
            json.dumps({"event": "MESSAGE", "space": "spaces/AAA"}).encode("utf-8")
        )
        assert len(ch._queue) == 1
        assert ch._queue[0] == {"event": "MESSAGE", "space": "spaces/AAA"}
        assert msg.ack_count == 1
        assert msg.nack_count == 0
    finally:
        await ch.disconnect()
        await asyncio.wait_for(task, timeout=1.0)


# --- Task 5.3 — malformed JSON nacked, queue unchanged --------------------


@pytest.mark.anyio("asyncio")
async def test_malformed_json_is_nacked_queue_unchanged() -> None:
    """Task 5.3 — non-JSON ``data`` triggers nack; queue length unchanged;
    callback returns without raising so the SubscriberClient stays running."""
    ch, fake = _build_channel()
    task = asyncio.create_task(ch.connect())
    try:
        await _wait_until(lambda: fake._callback is not None)
        msg_bad = fake.push_message(b"not-json")
        assert len(ch._queue) == 0
        assert msg_bad.nack_count == 1
        assert msg_bad.ack_count == 0
        # A subsequent good message still works — the callback survived.
        msg_good = fake.push_message(b'{"k":"v"}')
        assert len(ch._queue) == 1
        assert msg_good.ack_count == 1
    finally:
        await ch.disconnect()
        await asyncio.wait_for(task, timeout=1.0)


@pytest.mark.anyio("asyncio")
async def test_non_dict_json_is_nacked() -> None:
    """Task 5.3 (corollary) — JSON that decodes to a non-dict (e.g. a list
    or a scalar) is treated like malformed input: nacked, no enqueue."""
    ch, fake = _build_channel()
    task = asyncio.create_task(ch.connect())
    try:
        await _wait_until(lambda: fake._callback is not None)
        msg = fake.push_message(b'["not", "a", "dict"]')
        assert len(ch._queue) == 0
        assert msg.nack_count == 1
        assert msg.ack_count == 0
    finally:
        await ch.disconnect()
        await asyncio.wait_for(task, timeout=1.0)


# --- Task 5.4 — backoff schedule ------------------------------------------


@pytest.mark.anyio("asyncio")
async def test_backoff_schedule_follows_bounded_exponential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 5.4 — three consecutive streaming-pull failures yield sleep
    durations ``[1, 2, 4]`` in order (matches Decision: 入站 backoff 與
    last_error 上限直接複用 Discord 行為).

    Patches ``asyncio.sleep`` only inside ``cantus.serve.channels.googlechat``;
    other ``asyncio.sleep`` callers (notably the test's own polling
    helpers) still see the real implementation.
    """
    sleep_log: list[float] = []

    async def _capture_sleep(seconds: float) -> None:
        sleep_log.append(seconds)
        # Yield to the event loop without actually waiting so the channel
        # immediately starts its next attempt.
        return None

    # Patch the channel module's bound asyncio reference, not the global
    # asyncio module — the test's _wait_until helper imports asyncio
    # itself and must keep its real sleep.
    import cantus.serve.channels.googlechat as gc_mod

    # gc_mod.asyncio is the asyncio module imported by the channel; setting
    # its .sleep attribute patches the singleton seen by everyone, but the
    # patch is automatically rolled back by monkeypatch's teardown.
    monkeypatch.setattr(gc_mod.asyncio, "sleep", _capture_sleep, raising=True)  # type: ignore[attr-defined]

    settings = Settings(
        channel_google_chat_credentials_path=CREDENTIALS_PATH,
        channel_google_chat_subscription=SUBSCRIPTION,
        channel_google_chat_space=SPACE,
    )
    ch = GoogleChatPubSubChannel(settings=settings)

    failure_count = 0

    def _build_failing_subscriber() -> _FakeSubscriber:
        nonlocal failure_count
        failure_count += 1
        fake = _FakeSubscriber()
        original_subscribe = fake.subscribe

        def _subscribe(sub: str, callback: Any) -> Any:
            fut = original_subscribe(sub, callback=callback)
            fake.fail_future(RuntimeError(f"failure-{failure_count}"))
            return fut

        fake.subscribe = _subscribe  # type: ignore[method-assign,assignment]
        return fake

    ch._build_subscriber = _build_failing_subscriber  # type: ignore[method-assign]

    # The channel will rapidly accumulate failures because our patched
    # sleep returns immediately. Let it run to the 10-failure ceiling.
    await asyncio.wait_for(ch.connect(), timeout=2.0)

    # Sleeps recorded by the channel's backoff loop; the patched sleep
    # only captures gc_mod.asyncio.sleep calls so _wait_until-style
    # callers are not in this list. Channel sleeps 9 times before the
    # 10th failure exits without sleeping.
    # Note: patching gc_mod.asyncio.sleep is equivalent to patching the
    # real asyncio.sleep because Python modules are singletons, but the
    # other call sites in this test file run before patching takes hold
    # or after monkeypatch restores it.
    int_sleeps = [s for s in sleep_log if isinstance(s, int) or s >= 1]
    assert int_sleeps[:3] == [1, 2, 4]


# --- Task 5.5 — 10-failure ceiling sets last_error and stops --------------


@pytest.mark.anyio("asyncio")
async def test_ten_consecutive_failures_set_last_error_and_stop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 5.5 — after 10 consecutive streaming-pull failures the channel
    sets ``self.last_error`` and ``connect()`` returns cleanly without
    raising. No 11th SubscriberClient is constructed."""
    # Skip the backoff sleeps entirely so the test is fast.
    import cantus.serve.channels.googlechat as gc_mod

    async def _no_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(gc_mod.asyncio, "sleep", _no_sleep)  # type: ignore[attr-defined]

    settings = Settings(
        channel_google_chat_credentials_path=CREDENTIALS_PATH,
        channel_google_chat_subscription=SUBSCRIPTION,
        channel_google_chat_space=SPACE,
    )
    ch = GoogleChatPubSubChannel(settings=settings)

    build_count = 0
    exceptions_thrown: list[RuntimeError] = []

    def _build_failing_subscriber() -> _FakeSubscriber:
        nonlocal build_count
        build_count += 1
        exc = RuntimeError(f"failure-{build_count}")
        exceptions_thrown.append(exc)
        fake = _FakeSubscriber()
        original_subscribe = fake.subscribe

        def _subscribe(sub: str, callback: Any) -> Any:
            fut = original_subscribe(sub, callback=callback)
            fake.fail_future(exc)
            return fut

        fake.subscribe = _subscribe  # type: ignore[method-assign,assignment]
        return fake

    ch._build_subscriber = _build_failing_subscriber  # type: ignore[method-assign]

    # connect() should return cleanly once the 10th failure is recorded.
    await asyncio.wait_for(ch.connect(), timeout=2.0)

    # Exactly 10 attempts (no 11th).
    assert build_count == 10
    # last_error preserves the most recent exception instance.
    assert ch.last_error is exceptions_thrown[-1]


# --- Task 5.6 — ack ordering: enqueue first, then ack ---------------------


@pytest.mark.anyio("asyncio")
async def test_ack_after_enqueue_not_before() -> None:
    """Task 5.6 — when the queue append raises (e.g. memory error or a
    bug in the consumer), the message MUST be nacked rather than acked so
    Pub/Sub re-delivers it. This proves the contract `append-then-ack`
    (not `ack-then-append`).

    ``collections.deque`` is a C type so its ``append`` cannot be
    monkey-patched directly — we replace ``ch._queue`` wholesale with a
    list-like wrapper whose ``append`` raises on first call.
    """
    ch, fake = _build_channel()

    class _FlakyQueue:
        def __init__(self) -> None:
            self._inner: list[dict[str, Any]] = []
            self._raise_once = True

        def append(self, item: dict[str, Any]) -> None:
            if self._raise_once:
                self._raise_once = False
                raise RuntimeError("synthetic queue failure")
            self._inner.append(item)

        def __len__(self) -> int:
            return len(self._inner)

    ch._queue = _FlakyQueue()  # type: ignore[assignment]

    task = asyncio.create_task(ch.connect())
    try:
        await _wait_until(lambda: fake._callback is not None)
        msg = fake.push_message(b'{"k":"v"}')
        assert msg.ack_count == 0  # ack must NOT happen on enqueue failure
        assert msg.nack_count == 1  # nacked so Pub/Sub re-delivers
        assert len(ch._queue) == 0
    finally:
        await ch.disconnect()
        await asyncio.wait_for(task, timeout=1.0)

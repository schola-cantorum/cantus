"""Tests for the cantus base-exception policy.

Covers the ``cantus-base-exception-policy`` capability: production code
MUST NOT swallow base-tier signals (``asyncio.CancelledError``,
``KeyboardInterrupt``, ``SystemExit``). Two forms are permitted — a
*cleanup-then-reraise* block, and a narrow absorb of the
``CancelledError`` of a child task the code itself cancelled.

Requirement: Production code does not swallow BaseException-tier signals
  * best-effort cleanup does not swallow a base-tier signal
  * a message handler does not convert a base-tier signal into a nack
  * an ordinary Exception during cleanup is still tolerated
  * cleanup-then-reraise is a permitted form

Requirement: A codebase guard enforces the BaseException policy
  * guard passes on the conforming codebase
  * guard fails on a non-reraising BaseException catch
  * guard fails on a non-reraising cancellation catch
  * guard fails on a non-reraising interrupt or exit catch
  * guard fails on a base-tier exception inside a tuple
  * guard accepts the permitted narrow absorb
  * guard ignores an ordinary exception handler

Requirement: Cancellation propagates out of the channel connect and heartbeat
paths
  * a cancelled retry-backoff sleep propagates
  * a cancelled inbound-stream wait propagates
  * disconnect stops the pull without raising
  * a cancelled heartbeat child is absorbed by its parent
"""

from __future__ import annotations

import asyncio
import ast
import datetime as dt
import pathlib
from typing import Any
from unittest.mock import MagicMock

import pytest
import websockets
from websockets.asyncio.server import ServerConnection

import cantus
from cantus.config import Settings
from cantus.serve.channels._googlechat_internals import (
    _AccessTokenCache,
    _FakeMessage,
    _FakeSubscriber,
)
from cantus.serve.channels._realtime import GatewayClient
from cantus.serve.channels.googlechat import GoogleChatPubSubChannel
from tests.serve.channels.test_realtime_gateway import _send_hello, fake_gateway


# Stand-in inputs — none of these touch a real GCP project.
CREDENTIALS_PATH = "/tmp/sa.json"
SUBSCRIPTION = "projects/p/subscriptions/s"
SPACE = "spaces/AAA"


def _build_channel() -> GoogleChatPubSubChannel:
    """Construct a channel with no live transport wired up."""
    settings = Settings(
        channel_google_chat_credentials_path=CREDENTIALS_PATH,
        channel_google_chat_subscription=SUBSCRIPTION,
        channel_google_chat_space=SPACE,
    )
    return GoogleChatPubSubChannel(settings=settings)


class _ClosingSubscriber:
    """Subscriber stand-in whose ``close()`` raises a caller-chosen error."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc
        self.close_count = 0

    def close(self) -> None:
        self.close_count += 1
        raise self._exc


class _RaisingQueue:
    """Queue stand-in whose ``append`` raises a caller-chosen error.

    ``collections.deque`` is a C type so its ``append`` cannot be
    monkey-patched; the channel's ``_queue`` is replaced wholesale.
    """

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    def append(self, item: dict[str, Any]) -> None:
        raise self._exc

    def __len__(self) -> int:
        return 0


# --- Requirement: Production code does not swallow BaseException-tier signals


@pytest.mark.anyio("asyncio")
async def test_disconnect_propagates_keyboard_interrupt_from_close() -> None:
    """Scenario: best-effort cleanup does not swallow a base-tier signal.

    GIVEN a channel whose subscriber's ``close()`` raises KeyboardInterrupt
    WHEN ``disconnect()`` runs its best-effort close cleanup
    THEN the KeyboardInterrupt propagates out of ``disconnect()``
    """
    ch = _build_channel()
    subscriber = _ClosingSubscriber(KeyboardInterrupt())
    ch._subscriber = subscriber

    with pytest.raises(KeyboardInterrupt):
        await ch.disconnect()

    assert subscriber.close_count == 1


@pytest.mark.anyio("asyncio")
async def test_disconnect_tolerates_ordinary_exception_from_close() -> None:
    """Scenario: an ordinary Exception during cleanup is still tolerated.

    GIVEN a channel whose subscriber's ``close()`` raises a plain Exception
    WHEN ``disconnect()`` runs its best-effort close cleanup
    THEN ``disconnect()`` completes without raising
    """
    ch = _build_channel()
    subscriber = _ClosingSubscriber(RuntimeError("synthetic close failure"))
    ch._subscriber = subscriber

    await ch.disconnect()  # must not raise

    assert subscriber.close_count == 1
    assert ch._subscriber is None


def test_on_message_propagates_keyboard_interrupt_from_enqueue() -> None:
    """Scenario: a message handler does not convert a base-tier signal into a nack.

    GIVEN a channel whose queue ``append`` raises KeyboardInterrupt
    WHEN ``_on_message`` handles a well-formed message
    THEN the KeyboardInterrupt propagates and the message is NOT nacked
    """
    ch = _build_channel()
    # deque is a C type whose append cannot be patched; replace the queue
    # wholesale. The stand-in is intentionally not a deque, hence the ignore.
    ch._queue = _RaisingQueue(KeyboardInterrupt())  # type: ignore[assignment]
    msg = _FakeMessage(data=b'{"k":"v"}', attributes={})

    with pytest.raises(KeyboardInterrupt):
        ch._on_message(msg)

    assert msg.nack_count == 0
    assert msg.ack_count == 0


def test_on_message_nacks_on_ordinary_enqueue_failure() -> None:
    """An ordinary enqueue failure keeps the existing nack-and-return contract."""
    ch = _build_channel()
    # Same deque substitution as above; see that test for the rationale.
    ch._queue = _RaisingQueue(RuntimeError("synthetic queue failure"))  # type: ignore[assignment]
    msg = _FakeMessage(data=b'{"k":"v"}', attributes={})

    ch._on_message(msg)

    assert msg.nack_count == 1
    assert msg.ack_count == 0


@pytest.mark.anyio("asyncio")
async def test_ensure_token_drops_credentials_and_reraises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scenario: cleanup-then-reraise is a permitted form.

    GIVEN the token-refresh path whose ``refresh`` call raises
    WHEN the refresh fails
    THEN the cached credentials are dropped AND the exception is re-raised
    """
    creds = MagicMock()
    creds.token = "tok"
    # expiry in the past forces _needs_refresh() to be True.
    creds.expiry = dt.datetime.now(dt.timezone.utc).replace(
        tzinfo=None
    ) - dt.timedelta(minutes=1)

    def _refresh(_req: Any) -> None:
        raise RuntimeError("synthetic refresh failure")

    creds.refresh = _refresh

    def _from_file(path: str, scopes: list[str] | None = None) -> Any:
        return creds

    monkeypatch.setattr(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        _from_file,
    )

    cache = _AccessTokenCache(credentials_path=CREDENTIALS_PATH)

    with pytest.raises(RuntimeError, match="synthetic refresh failure"):
        await cache.get_token()

    assert cache._credentials is None


# --- Requirement: A codebase guard enforces the BaseException policy -------


# The signals the policy calls base-tier. ``asyncio.CancelledError`` and a
# bare ``CancelledError`` left by a ``from asyncio import`` line name the same
# signal, so only the final component of a reference is compared — a guard
# that recognised one spelling could be sidestepped by editing an import.
_BASE_TIER_NAMES = frozenset(
    {"BaseException", "CancelledError", "KeyboardInterrupt", "SystemExit"}
)


def _exception_name(node: ast.expr) -> str | None:
    """Final component of an exception reference, or None if it is not one."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _covers_base_tier(handler: ast.ExceptHandler) -> bool:
    """True when *handler* catches a base-tier signal, alone or in a tuple."""
    node = handler.type
    if node is None:  # bare `except:` also catches the base tier
        return True
    candidates = node.elts if isinstance(node, ast.Tuple) else [node]
    return any(_exception_name(c) in _BASE_TIER_NAMES for c in candidates)


def _find_non_reraising_base_tier_catches(source: str, label: str) -> list[str]:
    """Return a location per base-tier handler block that never re-raises.

    The policy permits *cleanup-then-reraise*: the handler body may do
    cleanup so long as the signal is re-raised. Any ``raise`` anywhere in
    the handler body satisfies that (mirroring "any subsequent indented
    line in the same block contains ``raise``").

    The other permitted form — a narrow absorb of a child task's
    cancellation — is written as ``contextlib.suppress(...)``, which is a
    ``with`` statement rather than an exception handler. It is outside what
    this scan examines, which is why no exemption list is needed.
    """
    violations: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            if not _covers_base_tier(handler):
                continue
            reraises = any(
                isinstance(inner, ast.Raise)
                for stmt in handler.body
                for inner in ast.walk(stmt)
            )
            if not reraises:
                violations.append(f"{label}:{handler.lineno}")
    return violations


def _scan_cantus_package() -> list[str]:
    root = pathlib.Path(cantus.__file__).parent
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        violations.extend(
            _find_non_reraising_base_tier_catches(
                path.read_text(encoding="utf-8"),
                str(path.relative_to(root.parent)),
            )
        )
    return violations


def test_guard_passes_on_the_conforming_codebase() -> None:
    """Scenario: guard passes on the conforming codebase.

    WHEN the guard scans the cantus package source
    THEN every handler covering a base-tier signal re-raises within its
         handler block
    """
    violations = _scan_cantus_package()

    assert violations == [], (
        "production handlers covering a base-tier signal that swallow it "
        "instead of re-raising: " + ", ".join(violations)
    )


def test_guard_fails_on_a_non_reraising_base_exception_catch() -> None:
    """Scenario: guard fails on a non-reraising BaseException catch.

    GIVEN a production block that catches BaseException and returns
          without re-raising
    WHEN the guard scans the source
    THEN the guard identifies the offending location
    """
    offending = """
def handler():
    try:
        do_work()
    except BaseException:
        return None
"""
    violations = _find_non_reraising_base_tier_catches(offending, "<sample>")

    assert violations == ["<sample>:5"]


def test_guard_accepts_the_cleanup_then_reraise_form() -> None:
    """The permitted cleanup-then-reraise form is not flagged."""
    conforming = """
def handler(self):
    try:
        do_work()
    except BaseException:
        self.state = None
        raise
"""
    assert _find_non_reraising_base_tier_catches(conforming, "<sample>") == []


def test_guard_fails_on_a_non_reraising_cancellation_catch() -> None:
    """Scenario: guard fails on a non-reraising cancellation catch.

    GIVEN a production block that catches ``asyncio.CancelledError`` and
          returns without re-raising
    WHEN the guard scans the source
    THEN the guard identifies the offending location

    Both spellings count. A module-qualified ``asyncio.CancelledError`` and
    a bare ``CancelledError`` left by a ``from asyncio import`` line name the
    same signal, so a guard that recognised only one would be a guard the
    next author could sidestep by changing an import.
    """
    qualified = """
def handler():
    try:
        do_work()
    except asyncio.CancelledError:
        return None
"""
    bare = """
def handler():
    try:
        do_work()
    except CancelledError:
        return None
"""
    assert _find_non_reraising_base_tier_catches(qualified, "<sample>") == ["<sample>:5"]
    assert _find_non_reraising_base_tier_catches(bare, "<sample>") == ["<sample>:5"]


def test_guard_fails_on_a_non_reraising_interrupt_or_exit_catch() -> None:
    """Scenario: guard fails on a non-reraising interrupt or exit catch.

    GIVEN a production block that catches ``KeyboardInterrupt`` or
          ``SystemExit`` and returns without re-raising
    WHEN the guard scans the source
    THEN the guard identifies the offending location
    """
    interrupt = """
def handler():
    try:
        do_work()
    except KeyboardInterrupt:
        return None
"""
    system_exit = """
def handler():
    try:
        do_work()
    except SystemExit:
        return None
"""
    assert _find_non_reraising_base_tier_catches(interrupt, "<sample>") == ["<sample>:5"]
    assert _find_non_reraising_base_tier_catches(system_exit, "<sample>") == ["<sample>:5"]


def test_guard_fails_on_a_base_tier_signal_inside_a_tuple() -> None:
    """Scenario: guard fails on a base-tier exception inside a tuple.

    GIVEN a handler naming a tuple of an ordinary exception type and a
          base-tier signal, which returns without re-raising
    WHEN the guard scans the source
    THEN the guard identifies the offending location
    """
    sample = """
def handler():
    try:
        do_work()
    except (ValueError, asyncio.CancelledError):
        return None
"""
    assert _find_non_reraising_base_tier_catches(sample, "<sample>") == ["<sample>:5"]


def test_guard_accepts_the_permitted_narrow_absorb() -> None:
    """Scenario: guard accepts the permitted narrow absorb.

    GIVEN production code that cancels a child task and awaits it inside
          ``contextlib.suppress(asyncio.CancelledError)``
    WHEN the guard scans the source
    THEN the guard does NOT report that code

    This is what makes an exemption list unnecessary. ``suppress`` is a
    context manager, so the permitted form is a ``With`` node and never
    reaches the handler scan at all.
    """
    permitted = """
async def shutdown(self):
    self._child.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await self._child
"""
    assert _find_non_reraising_base_tier_catches(permitted, "<sample>") == []


def test_guard_ignores_an_ordinary_exception_handler() -> None:
    """Scenario: guard ignores an ordinary exception handler.

    GIVEN production code that catches ``Exception`` and returns without
          re-raising
    WHEN the guard scans the source
    THEN the guard does NOT report that code
    """
    ordinary = """
def handler():
    try:
        do_work()
    except Exception:
        return None
"""
    assert _find_non_reraising_base_tier_catches(ordinary, "<sample>") == []


# --- Requirement: Cancellation propagates out of the channel connect and
#     heartbeat paths ---------------------------------------------------------


class _NullConnection:
    """WebSocket stand-in for a heartbeat loop that never gets that far."""

    async def close(self, code: int = 1000, reason: str = "") -> None:
        return None

    async def send(self, payload: str) -> None:
        return None


@pytest.mark.anyio("asyncio")
async def test_cancelled_heartbeat_child_propagates() -> None:
    """Scenario: a cancelled heartbeat child is absorbed by its parent (child half).

    GIVEN a heartbeat task waiting out its interval
    WHEN the task is cancelled
    THEN the CancelledError propagates out of the heartbeat task

    A child that returned instead would leave the parent's
    ``contextlib.suppress`` with nothing to absorb, which is the shape the
    policy forbids: the absorb belongs to whoever issued the cancel.
    """
    client = GatewayClient(gateway_url="ws://127.0.0.1:1")
    client._heartbeat_interval_ms = 3_600_000.0  # never fires during the test
    task = asyncio.create_task(
        client._heartbeat_loop(_NullConnection())  # type: ignore[arg-type]
    )
    await asyncio.sleep(0.01)  # let the loop reach its interval sleep
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.anyio("asyncio")
async def test_session_shutdown_absorbs_the_heartbeat_cancellation() -> None:
    """Scenario: a cancelled heartbeat child is absorbed by its parent (parent half).

    GIVEN a live gateway session whose heartbeat task the session started
    WHEN ``stop()`` ends the session
    THEN the session's shutdown completes without raising
    AND the socket reference is cleared, exactly as before this change
    """

    async def handler(ws: ServerConnection) -> None:
        await _send_hello(ws, heartbeat_interval=45000)
        try:
            async for _raw in ws:
                pass  # accept IDENTIFY, then hold the connection open
        except websockets.exceptions.ConnectionClosed:
            return

    async with fake_gateway(handler) as uri:
        client = GatewayClient(gateway_url=uri)
        started = asyncio.create_task(
            client.start(bot_token="t", intents=0, on_event=lambda _f: None)
        )
        for _ in range(200):  # wait for the session to own a socket
            if client._ws is not None:
                break
            await asyncio.sleep(0.01)
        assert client._ws is not None, "session never opened a socket"

        await client.stop()
        await started  # must not raise

    assert client._ws is None


@pytest.mark.anyio("asyncio")
async def test_cancelled_backoff_sleep_propagates() -> None:
    """Scenario: a cancelled retry-backoff sleep propagates.

    GIVEN a channel whose ``connect()`` is sleeping between reconnect
          attempts after a delivery failure
    WHEN the task running ``connect()`` is cancelled
    THEN the CancelledError propagates out of ``connect()``
    AND ``last_error`` still holds the delivery failure, not the cancellation
    """
    ch = _build_channel()

    def _failing_subscriber() -> Any:
        raise RuntimeError("synthetic subscribe failure")

    ch._build_subscriber = _failing_subscriber  # type: ignore[method-assign]

    task = asyncio.create_task(ch.connect())
    await asyncio.sleep(0.05)  # first failure recorded; the loop is now sleeping
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task

    # A cancellation is not a delivery failure, so it does not overwrite the
    # error that actually caused the backoff.
    assert isinstance(ch.last_error, RuntimeError)


async def _await_pull_future(sub: _FakeSubscriber) -> None:
    """Block until ``connect()`` has opened a streaming-pull future."""
    for _ in range(200):
        if sub._future is not None:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("connect() never opened a streaming-pull future")


@pytest.mark.anyio("asyncio")
async def test_disconnect_stops_the_pull_without_raising() -> None:
    """Scenario: disconnect stops the pull without raising.

    GIVEN a channel running its streaming pull
    WHEN ``disconnect()`` cancels the streaming-pull future
    THEN the awaited result returns rather than raises
    AND ``connect()`` observes the disconnected flag and returns cleanly

    The client library's future overrides ``cancel()`` to resolve with a
    result, so the shutdown path never reaches an exception handler.
    """
    ch = _build_channel()
    sub = _FakeSubscriber()
    ch._build_subscriber = lambda: sub  # type: ignore[method-assign,return-value]

    task = asyncio.create_task(ch.connect())
    await _await_pull_future(sub)

    await ch.disconnect()
    await task  # must not raise

    assert ch.last_error is None
    assert sub.closed


@pytest.mark.anyio("asyncio")
async def test_cancelled_inbound_stream_wait_propagates() -> None:
    """Scenario: a cancelled inbound-stream wait propagates.

    GIVEN a channel awaiting the streaming-pull result
    WHEN the task running ``connect()`` is cancelled from outside
    THEN the CancelledError propagates out of ``connect()``
    AND the cancellation is not counted as a delivery failure
    """
    ch = _build_channel()
    sub = _FakeSubscriber()
    ch._build_subscriber = lambda: sub  # type: ignore[method-assign,return-value]

    task = asyncio.create_task(ch.connect())
    await _await_pull_future(sub)
    assert sub._future is not None

    try:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        # The worker thread is still inside the fake future's blocking
        # result(); release it so it does not outlive the test.
        sub._future.trigger_done()

    assert ch.last_error is None

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
"""

from __future__ import annotations

import asyncio
import ast
import datetime as dt
import pathlib
from typing import Any
from unittest.mock import MagicMock

import pytest

import cantus
from cantus.config import Settings
from cantus.serve.channels._googlechat_internals import (
    _AccessTokenCache,
    _FakeMessage,
)
from cantus.serve.channels.googlechat import GoogleChatPubSubChannel


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


class _CancellingSubscriber:
    """Subscriber whose streaming-pull future raises CancelledError on result()."""

    def __init__(self) -> None:
        self._callback: Any = None
        self.closed = False

    def subscribe(self, subscription: str, callback: Any) -> Any:
        self._callback = callback
        return self

    def cancel(self) -> None:  # the pull future stand-in is self
        pass

    def result(self, timeout: float | None = None) -> None:
        raise asyncio.CancelledError()

    def close(self) -> None:
        self.closed = True


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


@pytest.mark.anyio("asyncio")
async def test_connect_reraises_external_cancellation() -> None:
    """An externally-injected CancelledError is not treated as a delivery failure.

    The retry loop must not fold a cancellation that did NOT come from
    ``disconnect()`` into its backoff schedule; it re-raises so the signal
    keeps propagating.
    """
    ch = _build_channel()
    sub = _CancellingSubscriber()
    ch._build_subscriber = lambda: sub  # type: ignore[method-assign]

    with pytest.raises(asyncio.CancelledError):
        await ch.connect()

    # Not recorded as a delivery failure.
    assert ch.last_error is None


@pytest.mark.anyio("asyncio")
async def test_connect_returns_quietly_when_cancelled_by_disconnect() -> None:
    """A cancellation caused by ``disconnect()`` exits the loop without raising."""
    ch = _build_channel()
    sub = _CancellingSubscriber()
    ch._build_subscriber = lambda: sub  # type: ignore[method-assign]
    ch._disconnected = True

    await ch.connect()  # must not raise

    assert ch.last_error is None


# --- Requirement: A codebase guard enforces the BaseException policy -------


def _catches_base_exception(handler: ast.ExceptHandler) -> bool:
    """True when *handler* catches ``BaseException``, alone or in a tuple."""
    node = handler.type
    if node is None:  # bare `except:` also catches the base tier
        return True
    candidates = node.elts if isinstance(node, ast.Tuple) else [node]
    return any(
        isinstance(c, ast.Name) and c.id == "BaseException" for c in candidates
    )


def _find_non_reraising_base_catches(source: str, label: str) -> list[str]:
    """Return a location per ``except BaseException`` block that never re-raises.

    The policy permits *cleanup-then-reraise*: the handler body may do
    cleanup so long as the signal is re-raised. Any ``raise`` anywhere in
    the handler body satisfies that (mirroring "any subsequent indented
    line in the same block contains ``raise``").
    """
    violations: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            if not _catches_base_exception(handler):
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
            _find_non_reraising_base_catches(
                path.read_text(encoding="utf-8"),
                str(path.relative_to(root.parent)),
            )
        )
    return violations


def test_guard_passes_on_the_conforming_codebase() -> None:
    """Scenario: guard passes on the conforming codebase.

    WHEN the guard scans the cantus package source
    THEN every ``except BaseException`` re-raises within its handler block
    """
    violations = _scan_cantus_package()

    assert violations == [], (
        "production `except BaseException` blocks that swallow the signal "
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
    violations = _find_non_reraising_base_catches(offending, "<sample>")

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
    assert _find_non_reraising_base_catches(conforming, "<sample>") == []

"""cantus.serve.channels._googlechat_internals — private helpers for the
Google Chat over Pub/Sub channel adapter.

This module is INTERNAL (leading underscore + no public re-export). It hosts
two pieces that exist only to support
:class:`cantus.serve.channels.googlechat.GoogleChatPubSubChannel`:

1. :class:`_AccessTokenCache` — lazy OAuth2 access token cache backed by a
   service-account JSON file. The file is read on the first
   ``get_token()`` call; minted tokens are cached in memory and refreshed
   when the expiry falls within a 5-minute buffer. Refresh failures
   propagate to the caller AND drop the cached credentials so the next
   call re-reads the SA file (picks up rotation on disk; avoids retaining
   broken state).
2. :class:`_FakeSubscriber` — minimal in-memory stand-in for
   ``google.cloud.pubsub_v1.SubscriberClient`` used by the tests under
   ``tests/serve/channels/`` to drive the channel callback without
   touching a live GCP project. Lives in the runtime module so the
   channel's lifecycle code can be tested in isolation; production
   ``connect()`` constructs the real ``SubscriberClient``.
"""

from __future__ import annotations

import asyncio
import datetime as _dt
import logging
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from google.cloud.pubsub_v1.subscriber.message import Message
    from google.oauth2.service_account import Credentials


logger = logging.getLogger("cantus.serve.channels")


# OAuth2 scope required by the Google Chat REST API ``create_message``
# call. See https://developers.google.com/workspace/chat/api/reference/rest
# and https://developers.google.com/identity/protocols/oauth2/scopes#chat
_GOOGLE_CHAT_SCOPES = ["https://www.googleapis.com/auth/chat.bot"]

# Re-mint the token when the current one expires within this many seconds
# from now. Five minutes is the established Google client library default
# and gives every dispatched ``send()`` enough headroom even if the request
# stalls behind a slow ``asyncio.to_thread`` reschedule.
_REFRESH_BUFFER = _dt.timedelta(minutes=5)


class _AccessTokenCache:
    """Lazy OAuth2 access token cache backed by a service-account JSON file.

    The cache is private to a single ``GoogleChatPubSubChannel`` instance
    — there is no global state. The service-account JSON is read from
    disk on the first ``get_token()`` call (NOT at construction time) so
    a misconfigured ``credentials_path`` surfaces as a clear filesystem
    error only when an actual outbound send is attempted.
    """

    def __init__(self, credentials_path: str) -> None:
        self._credentials_path = credentials_path
        self._credentials: Credentials | None = None

    async def get_token(self) -> str:
        """Return a valid OAuth2 access token, minting or refreshing as needed.

        Raises whatever google-auth raises from ``from_service_account_file``
        (e.g. ``FileNotFoundError``, ``ValueError``) on first call, and
        whatever ``credentials.refresh()`` raises on subsequent refresh
        failures. On refresh failure the cached credentials are dropped so
        the next call re-reads the SA file from disk.
        """
        if self._credentials is None:
            from google.oauth2.service_account import Credentials as _Creds

            # google-auth lacks py.typed; strict mypy flags the call as
            # untyped despite the ignore_missing_imports override.
            self._credentials = _Creds.from_service_account_file(  # type: ignore[no-untyped-call]
                self._credentials_path,
                scopes=_GOOGLE_CHAT_SCOPES,
            )
        if self._needs_refresh():
            from google.auth.transport.requests import Request

            try:
                await asyncio.to_thread(self._credentials.refresh, Request())
            except BaseException:
                # Drop the credentials so the next call re-reads the SA
                # file (covers on-disk rotation) and re-attempts refresh
                # rather than retaining a broken object.
                self._credentials = None
                raise
        return str(self._credentials.token)

    def _needs_refresh(self) -> bool:
        assert self._credentials is not None
        expiry = self._credentials.expiry
        if expiry is None:
            # google-auth populates expiry after the first successful
            # refresh. None means "never refreshed" → must refresh now.
            return True
        # google-auth stores expiry as a naive datetime in UTC. Compare in
        # the same naive-UTC space to avoid timezone-arithmetic mismatches.
        now_utc_naive = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
        # bool() coercion is needed because google-auth's expiry attribute
        # is dynamically-typed; strict mypy otherwise flags the comparison
        # as returning Any.
        return bool((expiry - now_utc_naive) < _REFRESH_BUFFER)


class _FakeSubscriber:
    """In-memory stand-in for ``google.cloud.pubsub_v1.SubscriberClient``.

    Used by ``tests/serve/channels/test_googlechat_*`` to drive
    ``GoogleChatPubSubChannel`` without touching a live GCP project. The
    contract is intentionally narrow — only the methods ``connect()``
    actually invokes on the real client are emulated.

    Push messages into the channel callback via :meth:`push_message`. The
    helper builds a ``_FakeMessage`` with ``ack()``/``nack()`` counters so
    tests can assert ack/nack discipline.
    """

    def __init__(self) -> None:
        self._callback: Callable[[Message], None] | None = None
        self._future: _FakeStreamingPullFuture | None = None
        self.subscription_path_called: str | None = None
        self.closed = False

    def subscribe(
        self,
        subscription: str,
        callback: Callable[[Any], None],
    ) -> _FakeStreamingPullFuture:
        self.subscription_path_called = subscription
        self._callback = callback
        self._future = _FakeStreamingPullFuture()
        return self._future

    def close(self) -> None:
        self.closed = True

    def push_message(self, data: bytes, *, attributes: dict[str, str] | None = None) -> _FakeMessage:
        """Drive the registered callback with a synthetic Pub/Sub message."""
        if self._callback is None:
            raise RuntimeError(
                "_FakeSubscriber.push_message called before subscribe() registered "
                "a callback"
            )
        msg = _FakeMessage(data=data, attributes=attributes or {})
        self._callback(msg)
        return msg

    def fail_future(self, exc: BaseException) -> None:
        """Cause the streaming-pull future to raise *exc* on its blocked ``result()``.

        Mirrors how the real ``SubscriberClient`` surfaces server-side
        errors via the StreamingPullFuture: sets the pending error and
        unblocks the waiter so the caller of ``result()`` (running on a
        worker thread via ``asyncio.to_thread`` in :meth:`connect`)
        immediately re-raises *exc*.
        """
        if self._future is None:
            raise RuntimeError(
                "_FakeSubscriber.fail_future called before subscribe()"
            )
        self._future._pending_error = exc
        self._future._done_event.set()


class _FakeStreamingPullFuture:
    """Minimal stand-in for ``google.cloud.pubsub_v1.subscriber.futures.StreamingPullFuture``.

    Only exposes the surface ``connect()`` consults: a SYNC ``result()``
    (matching the real ``concurrent.futures.Future``-style API; the real
    ``connect()`` invokes it through :func:`asyncio.to_thread`) and a
    ``cancel()`` so ``disconnect()`` can stop the pull. Tests can trigger
    an exception via :meth:`_FakeSubscriber.fail_future` or unblock the
    sync ``result()`` via :meth:`trigger_done`.
    """

    def __init__(self) -> None:
        self._cancelled = False
        self._pending_error: BaseException | None = None
        # threading.Event is the right primitive here because ``result()``
        # runs on a worker thread via ``asyncio.to_thread``, and
        # ``cancel()`` is invoked from the event loop. asyncio.Event is
        # not thread-safe.
        import threading

        self._done_event = threading.Event()

    def cancel(self) -> None:
        self._cancelled = True
        self._done_event.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def result(self, timeout: float | None = None) -> None:
        # The real future blocks the caller until cancellation or error.
        # Tests trigger an error by calling fail_future, then unblock via
        # this event.
        self._done_event.wait(timeout=timeout)
        if self._pending_error is not None:
            raise self._pending_error

    def trigger_done(self) -> None:
        """Test helper: unblock ``result()`` without an error."""
        self._done_event.set()


class _FakeMessage:
    """Stand-in for ``google.cloud.pubsub_v1.subscriber.message.Message``."""

    def __init__(self, *, data: bytes, attributes: dict[str, str]) -> None:
        self.data = data
        self.attributes = attributes
        self.ack_count = 0
        self.nack_count = 0

    def ack(self) -> None:
        self.ack_count += 1

    def nack(self) -> None:
        self.nack_count += 1


__all__: list[str] = []  # private module — nothing re-exported

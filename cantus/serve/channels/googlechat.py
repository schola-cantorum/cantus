"""cantus.serve.channels.googlechat — Google Chat over Pub/Sub channel adapter (v0.4.7).

Implements :class:`cantus.serve.channel.RealtimeChannel` ONLY. Pub/Sub pull
is inherently long-lived and inbound-by-async-callback, so the FastAPI
``lifespan`` dispatches :meth:`GoogleChatPubSubChannel.connect` as a
background task; there is no HTTP webhook route to mount. Outbound replies
post to the Google Chat REST API via the app-scoped
:class:`httpx.AsyncClient` with an OAuth2 bearer token minted from a
service-account JSON file. See ``docs/cookbook-google-chat-channel.md``
for the student-facing walkthrough.

Cross-platform wheel matrix
---------------------------

Linux x86_64 (manylinux2014) / macOS arm64 (Apple Silicon) / macOS x86_64
(Intel) / Windows AMD64, all × CPython 3.10, 3.11, 3.12, 3.13. The new
B3 dependency ``google-cloud-pubsub>=2.20,<3`` and its transitive
``grpcio`` publish prebuilt wheels for that matrix; see ``pyproject.toml``
``[project.optional-dependencies] serve`` for the exact version pins.

Security discipline
-------------------

The constructor refuses to land any of ``credentials_path`` /
``subscription`` / ``space`` from a blank or whitespace-only string source
(sourced from the constructor argument, Settings, or — for
``credentials_path`` only — the ``GOOGLE_APPLICATION_CREDENTIALS``
environment variable used by Google's Application Default Credentials
chain). The error message is a fixed constant with no echoed value —
including the file path, which can itself reveal deployment topology.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import deque
from typing import TYPE_CHECKING, Any

from cantus.config import Settings
from cantus.serve.channels._errors import ChannelSendError
from cantus.serve.channels._googlechat_internals import _AccessTokenCache

if TYPE_CHECKING:
    from google.cloud.pubsub_v1 import SubscriberClient
    from google.cloud.pubsub_v1.subscriber.futures import StreamingPullFuture
    from google.cloud.pubsub_v1.subscriber.message import Message


logger = logging.getLogger("cantus.serve.channels")


# Fixed constants used so str(exception) cannot leak any input value.
_MISSING_CONFIG_MESSAGE = (
    "GoogleChatPubSubChannel requires credentials_path, subscription, and space"
)
_MISSING_SPACE_MESSAGE = (
    "must carry 'space' or set Settings.channel_google_chat_space"
)
_BODY_EXCERPT_LIMIT = 200
_GOOGLE_CHAT_API_BASE = "https://chat.googleapis.com/v1"

# Backoff schedule matches v0.4.6 Discord IDENTIFY ceiling exactly so the
# operational behavior stays uniform across realtime channels.
_MAX_BACKOFF_SECONDS = 60
_MAX_CONSECUTIVE_FAILURES = 10


def _coerce_str(value: str | None) -> str | None:
    """Normalise ``str``/``None`` so blank or whitespace-only is ``None``.

    Mirrors the discipline used by the v0.4.5 webhook channels and v0.4.6
    Discord channel: the contract is "blank means missing", so callers
    can supply ``""`` from a missing Settings field without tripping a
    successful construction.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    if not value.strip():
        return None
    return value


class GoogleChatPubSubChannel:
    """Google Chat channel adapter — conforms to ``RealtimeChannel`` ONLY.

    The constructor takes three positional arguments OR a
    :class:`cantus.config.Settings` object (constructor args win). For
    ``credentials_path`` only, a third fallback consults the
    ``GOOGLE_APPLICATION_CREDENTIALS`` environment variable so a deployment
    that already uses Google's Application Default Credentials chain need
    not duplicate the path into the cantus-specific Settings field. A
    missing value (after the full chain) raises :class:`ValueError` with
    the fixed message :data:`_MISSING_CONFIG_MESSAGE` that NEVER echoes
    any supplied value.

    The class deliberately does NOT define ``mount`` — Pub/Sub pull is the
    sole inbound transport, no HTTP route is required, and
    ``isinstance(channel, WebhookChannel)`` MUST evaluate to ``False`` so
    :func:`cantus.serve.serve` does not attempt to call ``mount`` on it.
    """

    def __init__(
        self,
        credentials_path: str | None = None,
        subscription: str | None = None,
        space: str | None = None,
        *,
        queue_maxlen: int | None = None,
        settings: Settings | None = None,
    ) -> None:
        effective_settings = settings if settings is not None else Settings()

        resolved_credentials_path = (
            _coerce_str(credentials_path)
            or _coerce_str(effective_settings.channel_google_chat_credentials_path)
            or _coerce_str(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
        )
        resolved_subscription = _coerce_str(subscription) or _coerce_str(
            effective_settings.channel_google_chat_subscription
        )
        resolved_space = _coerce_str(space) or _coerce_str(
            effective_settings.channel_google_chat_space
        )

        if (
            resolved_credentials_path is None
            or resolved_subscription is None
            or resolved_space is None
        ):
            raise ValueError(_MISSING_CONFIG_MESSAGE)

        self._credentials_path: str = resolved_credentials_path
        self._subscription: str = resolved_subscription
        self._default_space: str = resolved_space
        self._queue: deque[dict[str, Any]] = deque(maxlen=queue_maxlen)
        self._queue_maxlen: int | None = queue_maxlen
        self._token_cache = _AccessTokenCache(self._credentials_path)
        self._subscriber: SubscriberClient | None = None
        self._pull_future: StreamingPullFuture | None = None
        self._app: Any = None  # FastAPI is bound lazily on first send()
        self._disconnected = False
        self.last_error: BaseException | None = None

    # ----- Channel surface ------------------------------------------------

    def receive(self) -> dict[str, Any]:
        """Return the next inbound Pub/Sub event as a ``dict``.

        Pops the oldest entry from the channel's internal ``deque``. An
        empty queue raises :class:`IndexError` with the literal substring
        ``GoogleChatPubSubChannel queue is empty`` (mirrors
        :class:`cantus.serve.channel.LocalMockReceiver`'s diagnostic
        contract).
        """
        if not self._queue:
            raise IndexError("GoogleChatPubSubChannel queue is empty")
        return self._queue.popleft()

    async def send(self, message: dict[str, Any]) -> None:
        """Dispatch one outbound message to a Google Chat space.

        Routing:

        * ``message["space"]`` if present and non-empty, else the default
          space resolved from Settings at construction time.
        * If both are absent → :class:`ValueError` with the fixed message.

        The OAuth2 bearer token is minted on demand via
        :class:`_AccessTokenCache` and attached as the ``Authorization``
        header. HTTP 4xx/5xx surfaces as
        :class:`cantus.serve.channels.ChannelSendError` with
        ``provider="google_chat"``; the token never enters the exception.
        """
        space = message.get("space") or self._default_space
        if not space:
            raise ValueError(_MISSING_SPACE_MESSAGE)
        if self._app is None:
            raise RuntimeError(
                "GoogleChatPubSubChannel.send requires an app-scoped http_client; "
                "call serve(registry, channels=[...]) so the lifespan can bind one."
            )

        token = await self._token_cache.get_token()
        url = f"{_GOOGLE_CHAT_API_BASE}/spaces/{space}/messages"
        body = message.get("data", {})
        client = self._app.state.http_client
        response = await client.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )
        if 400 <= response.status_code < 600:
            body_excerpt = response.text[:_BODY_EXCERPT_LIMIT]
            raise ChannelSendError(
                status_code=response.status_code,
                body_excerpt=body_excerpt,
                provider="google_chat",
            )

    # ----- RealtimeChannel surface ----------------------------------------

    async def connect(self) -> None:
        """Open the long-lived Pub/Sub streaming pull subscription.

        Each delivered ``PubsubMessage`` is parsed as UTF-8 JSON,
        appended to the channel's internal ``deque``, then acked. Malformed
        JSON is nacked and the callback returns without raising so the
        ``SubscriberClient`` can keep running. When the underlying
        streaming-pull future raises, ``connect()`` waits ``min(60, 2**n)``
        seconds and reopens; after 10 consecutive failures with no
        intervening successful delivery the method sets ``self.last_error``
        and returns cleanly without raising — so the FastAPI lifespan
        task does not crash.
        """
        attempts = 0
        while not self._disconnected:
            try:
                self._subscriber = self._build_subscriber()
                self._pull_future = self._subscriber.subscribe(
                    self._subscription,
                    callback=self._on_message,
                )
                # _pull_future.result() blocks until cancellation or error.
                # We await it via to_thread so cancellation from
                # disconnect() can take effect.
                await asyncio.to_thread(self._pull_future.result)
                # Clean exit (cancellation): reset for any further restart
                # attempts a caller might trigger.
                attempts = 0
                if self._disconnected:
                    return
            except BaseException as exc:
                self.last_error = exc
                attempts += 1
                if attempts >= _MAX_CONSECUTIVE_FAILURES:
                    return
                # Backoff schedule: after failure N (1-indexed), sleep
                # min(60, 2^(N-1)) seconds. First failure → 1s; second → 2s;
                # third → 4s; …; after the 10th failure we exit without
                # another sleep so the ceiling is exactly 10 attempts.
                delay = min(_MAX_BACKOFF_SECONDS, 2 ** (attempts - 1))
                try:
                    await asyncio.sleep(delay)
                except asyncio.CancelledError:
                    return
            finally:
                # Close the per-attempt subscriber so the next iteration
                # creates a fresh one. The real SubscriberClient supports
                # close() idempotently.
                if self._subscriber is not None:
                    try:
                        self._subscriber.close()
                    except BaseException:  # noqa: BLE001 — defensive
                        pass
                    self._subscriber = None

    async def disconnect(self) -> None:
        """Cancel the streaming pull and close the SubscriberClient.

        Idempotent: calling before ``connect()`` returns silently, and
        repeated calls are a no-op so the FastAPI lifespan can shut down
        defensively without raising.
        """
        if self._disconnected:
            return
        self._disconnected = True
        if self._pull_future is not None:
            try:
                self._pull_future.cancel()
            except BaseException:  # noqa: BLE001 — defensive
                pass
        if self._subscriber is not None:
            try:
                self._subscriber.close()
            except BaseException:  # noqa: BLE001 — defensive
                pass
            self._subscriber = None

    # ----- Internal helpers -----------------------------------------------

    def _build_subscriber(self) -> SubscriberClient:
        """Construct a real SubscriberClient bound to the SA credentials.

        Lazy import so ``import cantus.serve`` does not require
        google-cloud-pubsub unless a channel instance is actually
        constructed. Tests monkey-patch this method to inject the
        :class:`_FakeSubscriber` stand-in.
        """
        from google.cloud.pubsub_v1 import SubscriberClient as _SC
        from google.oauth2.service_account import Credentials as _Creds

        # google-auth lacks py.typed; strict mypy flags the call as
        # untyped despite the ignore_missing_imports override.
        creds = _Creds.from_service_account_file(self._credentials_path)  # type: ignore[no-untyped-call]
        return _SC(credentials=creds)

    def _on_message(self, message: Message) -> None:
        """Callback invoked by SubscriberClient for each delivered message.

        Parses the message ``data`` as UTF-8 JSON; on success enqueues
        the resulting dict then acks; on parse failure nacks and returns
        without raising. The ack ordering — append BEFORE ack — guarantees
        that a queue-append failure leaves the message unacked so Pub/Sub
        re-delivers it.
        """
        try:
            payload = json.loads(message.data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            message.nack()
            return
        if not isinstance(payload, dict):
            message.nack()
            return
        try:
            self._queue.append(payload)
        except BaseException:  # noqa: BLE001 — defensive: nack on enqueue failure
            message.nack()
            return
        message.ack()


__all__ = ["GoogleChatPubSubChannel"]

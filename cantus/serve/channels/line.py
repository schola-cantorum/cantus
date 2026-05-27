"""cantus.serve.channels.line — LINE Messaging API webhook channel.

Inbound: ``POST /channels/line`` route that verifies ``X-Line-Signature``
via HMAC-SHA256 over the raw body, then enqueues the platform JSON event.
Outbound: ``send(message)`` POSTs to ``api.line.me`` reply endpoint via
the app-scoped ``httpx.AsyncClient`` stored on ``app.state.http_client``.

Failures on either path return / raise indistinguishable surfaces — 401
with the byte-identical body ``{"detail": "Authentication required"}`` for
inbound, :class:`ChannelSendError` for outbound — so signature material
never leaks via response shape or exception message.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request

from cantus.config import Settings
from cantus.serve.channels._errors import ChannelSendError
from cantus.serve.channels._signing import resolve_secret, verify_line_signature

if TYPE_CHECKING:
    from fastapi import FastAPI

_LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
_AUTH_REQUIRED_DETAIL = "Authentication required"
_BODY_EXCERPT_LIMIT = 200

logger = logging.getLogger("cantus.serve.channels")


class LineWebhookChannel:
    """Conforms to :class:`cantus.serve.channel.WebhookChannel`."""

    def __init__(
        self,
        channel_secret: str | None = None,
        channel_access_token: str | None = None,
        queue_maxlen: int | None = None,
        settings: Settings | None = None,
    ) -> None:
        effective_settings = settings if settings is not None else Settings()
        self._channel_secret: str = resolve_secret(
            channel_secret,
            effective_settings.channel_line_secret,
            "channel_line_secret",
            "line",
        )
        self._channel_access_token: str = resolve_secret(
            channel_access_token,
            effective_settings.channel_line_access_token,
            "channel_line_access_token",
            "line",
        )
        self._queue: deque[dict[str, Any]] = deque(maxlen=queue_maxlen)
        self._queue_maxlen = queue_maxlen
        self._app: FastAPI | None = None

    def mount(self, app: FastAPI) -> None:
        self._app = app

        async def _handler(request: Request) -> dict[str, Any]:
            raw = await request.body()
            sig = request.headers.get("x-line-signature")
            if not verify_line_signature(self._channel_secret, raw, sig):
                raise HTTPException(
                    status_code=401, detail=_AUTH_REQUIRED_DETAIL
                )
            event = json.loads(raw.decode("utf-8"))
            if (
                self._queue_maxlen is not None
                and len(self._queue) >= self._queue_maxlen
            ):
                logger.warning(
                    "LineWebhookChannel queue at maxlen=%d; dropped oldest event",
                    self._queue_maxlen,
                )
            self._queue.append(event)
            return {"ok": True}

        app.add_api_route(
            path="/channels/line",
            endpoint=_handler,
            methods=["POST"],
            name="line_webhook",
            summary="LINE Messaging API webhook receiver",
        )

    def receive(self) -> dict[str, Any]:
        if not self._queue:
            raise IndexError("LineWebhookChannel queue is empty")
        return self._queue.popleft()

    async def send(self, message: dict[str, Any]) -> None:
        if self._app is None:
            raise RuntimeError(
                "LineWebhookChannel.send requires mount(app) to have been "
                "called and app.state.http_client populated by the FastAPI "
                "lifespan."
            )
        client = self._app.state.http_client
        response = await client.post(
            _LINE_REPLY_URL,
            json=message,
            headers={
                "Authorization": f"Bearer {self._channel_access_token}",
                "Content-Type": "application/json",
            },
        )
        if 400 <= response.status_code < 600:
            raise ChannelSendError(
                status_code=response.status_code,
                body_excerpt=response.text[:_BODY_EXCERPT_LIMIT],
                provider="line",
            )


__all__ = ["LineWebhookChannel"]

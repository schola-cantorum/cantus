"""cantus.serve.channels.telegram — Telegram Bot API webhook channel.

Inbound: ``POST /channels/telegram`` route that compares the
``X-Telegram-Bot-Api-Secret-Token`` header against the channel's configured
``secret_token`` via :func:`hmac.compare_digest`, then enqueues the platform
JSON update.

Outbound: ``send(message)`` POSTs to ``api.telegram.org/bot<token>/sendMessage``
via the app-scoped ``httpx.AsyncClient`` stored on ``app.state.http_client``.
``str()`` and ``repr()`` of the raised :class:`ChannelSendError` MUST NOT
contain the bot token; only the response body excerpt (4xx/5xx) is carried.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request

from cantus.config import Settings
from cantus.serve.channels._errors import ChannelSendError
from cantus.serve.channels._signing import constant_time_compare, resolve_secret

if TYPE_CHECKING:
    from fastapi import FastAPI

_AUTH_REQUIRED_DETAIL = "Authentication required"
_BODY_EXCERPT_LIMIT = 200

logger = logging.getLogger("cantus.serve.channels")


class TelegramWebhookChannel:
    """Conforms to :class:`cantus.serve.channel.WebhookChannel`."""

    def __init__(
        self,
        secret_token: str | None = None,
        bot_token: str | None = None,
        queue_maxlen: int | None = None,
        settings: Settings | None = None,
    ) -> None:
        effective_settings = settings if settings is not None else Settings()
        self._secret_token: str = resolve_secret(
            secret_token,
            effective_settings.channel_telegram_secret_token,
            "channel_telegram_secret_token",
            "telegram",
        )
        self._bot_token: str = resolve_secret(
            bot_token,
            effective_settings.channel_telegram_bot_token,
            "channel_telegram_bot_token",
            "telegram",
        )
        self._queue: deque[dict[str, Any]] = deque(maxlen=queue_maxlen)
        self._queue_maxlen = queue_maxlen
        self._app: FastAPI | None = None

    def mount(self, app: FastAPI) -> None:
        self._app = app

        async def _handler(request: Request) -> dict[str, Any]:
            provided = request.headers.get("x-telegram-bot-api-secret-token")
            if not constant_time_compare(provided, self._secret_token):
                raise HTTPException(
                    status_code=401, detail=_AUTH_REQUIRED_DETAIL
                )
            event = await request.json()
            if (
                self._queue_maxlen is not None
                and len(self._queue) >= self._queue_maxlen
            ):
                logger.warning(
                    "TelegramWebhookChannel queue at maxlen=%d; dropped oldest event",
                    self._queue_maxlen,
                )
            self._queue.append(event)
            return {"ok": True}

        app.add_api_route(
            path="/channels/telegram",
            endpoint=_handler,
            methods=["POST"],
            name="telegram_webhook",
            summary="Telegram Bot API webhook receiver",
        )

    def receive(self) -> dict[str, Any]:
        if not self._queue:
            raise IndexError("TelegramWebhookChannel queue is empty")
        return self._queue.popleft()

    async def send(self, message: dict[str, Any]) -> None:
        if self._app is None:
            raise RuntimeError(
                "TelegramWebhookChannel.send requires mount(app) to have been "
                "called and app.state.http_client populated by the FastAPI "
                "lifespan."
            )
        client = self._app.state.http_client
        url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
        response = await client.post(
            url,
            json=message,
            headers={"Content-Type": "application/json"},
        )
        if 400 <= response.status_code < 600:
            raise ChannelSendError(
                status_code=response.status_code,
                body_excerpt=response.text[:_BODY_EXCERPT_LIMIT],
                provider="telegram",
            )


__all__ = ["TelegramWebhookChannel"]

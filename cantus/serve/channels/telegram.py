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
import re
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

# Telegram bot_token = `<bot_id>:<token>` per the Bot API docs; the suffix is
# at least 35 chars in practice but 20 is the smallest plausible random
# component we accept. Total length capped at 255 to keep error paths bounded.
_BOT_TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]{20,}$")
_BOT_TOKEN_MAX_LEN = 255
# Telegram secret_token (X-Telegram-Bot-Api-Secret-Token) allows 1..256 chars
# from A-Z, a-z, 0-9, underscore, hyphen.
_SECRET_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_SECRET_TOKEN_MAX_LEN = 256

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
        # Format validation runs AFTER resolve_secret's blank/missing check so
        # an unset env still surfaces "channel secret not configured", not
        # "invalid format". Error messages never echo the rejected value to
        # avoid leaking partial secrets via logs / TestClient capture.
        if (
            len(self._bot_token) > _BOT_TOKEN_MAX_LEN
            or _BOT_TOKEN_RE.fullmatch(self._bot_token) is None
        ):
            raise ValueError("telegram bot_token has invalid format")
        if (
            len(self._secret_token) > _SECRET_TOKEN_MAX_LEN
            or _SECRET_TOKEN_RE.fullmatch(self._secret_token) is None
        ):
            raise ValueError("telegram secret_token has invalid format")
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

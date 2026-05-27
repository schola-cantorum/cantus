"""cantus.serve.channels.discord — Discord channel adapter (v0.4.6).

Implements both :class:`cantus.serve.channel.RealtimeChannel` (Discord
Gateway WebSocket via :class:`cantus.serve.channels._realtime.GatewayClient`)
and :class:`cantus.serve.channel.WebhookChannel` (Ed25519-signed Interactions
HTTP endpoint via :mod:`cantus.serve.channels._ed25519`). Discord is the only
shipped adapter that conforms to both sub-Protocols — the bot loop demands a
long-lived WebSocket and slash-command callbacks demand an HTTP receiver, and
both share the same bot_token / public_key / application_id triple, so a
single adapter class is the cleanest mapping to the Discord developer mental
model. See ``docs/cookbook-discord-channel.md`` for the student-facing
walkthrough.

Cross-platform wheel matrix
---------------------------

Linux x86_64 (manylinux2014) / macOS arm64 (Apple Silicon) / macOS x86_64
(Intel) / Windows AMD64, all × CPython 3.10, 3.11, 3.12, 3.13. Both new
B2 dependencies — ``pynacl>=1.5,<2`` and ``websockets>=13`` — publish
prebuilt wheels for that matrix; see ``pyproject.toml``
``[project.optional-dependencies] serve`` for the exact version pins.

Security discipline
-------------------

The constructor refuses to land any of ``bot_token`` / ``public_key`` /
``application_id`` from a blank or whitespace-only string source (sourced
either from the constructor argument or from ``Settings``); the error
message is a fixed constant with no echoed secret value. The interactions
HTTP endpoint returns the byte-identical 401 body
``{"detail":"Authentication required"}`` for every signature failure mode
(missing header, malformed hex, bad signature, wrong length, mathematically
invalid signature). The outbound ``Authorization: Bot <token>`` header is
attached ONLY to the channel-message path (``/api/v10/channels/.../messages``);
interaction callbacks deliberately omit the header because Discord's
contract treats the interaction token itself as the proof of authority.
"""

from __future__ import annotations

import binascii
import json
import logging
from collections import deque
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import SecretStr

from cantus.config import Settings
from cantus.serve.channels._ed25519 import (
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    DiscordSignatureError,
    verify_ed25519,
)
from cantus.serve.channels._errors import ChannelSendError
from cantus.serve.channels._realtime import GatewayClient

if TYPE_CHECKING:
    pass


logger = logging.getLogger("cantus.serve.channels")


# Discord Gateway intent bit values (v10 docs):
# https://discord.com/developers/docs/topics/gateway#gateway-intents
_INTENT_GUILDS = 1 << 0           # = 1
_INTENT_GUILD_MESSAGES = 1 << 9   # = 512
_INTENT_DIRECT_MESSAGES = 1 << 12  # = 4096
_INTENT_MESSAGE_CONTENT = 1 << 15  # = 32768

#: Default Gateway intent bitmask — the minimal set for a student-grade
#: echo bot: GUILDS (READY/GUILD_CREATE), GUILD_MESSAGES (text-channel
#: events), DIRECT_MESSAGES (DM events), and the privileged
#: MESSAGE_CONTENT (must be enabled in the Discord Developer Portal).
DEFAULT_INTENTS = (
    _INTENT_GUILDS
    | _INTENT_GUILD_MESSAGES
    | _INTENT_MESSAGE_CONTENT
    | _INTENT_DIRECT_MESSAGES
)

# Fixed constants used so str(exception) and the 401 body cannot leak material.
_MISSING_SECRET_MESSAGE = (
    "DiscordRealtimeChannel requires bot_token, public_key, and application_id"
)
_AUTH_REQUIRED_DETAIL = "Authentication required"
_BODY_EXCERPT_LIMIT = 200
_DISCORD_API_BASE = "https://discord.com/api/v10"
_INTERACTIONS_ROUTE = "/channels/discord/interactions"


def _coerce_secret(
    value: str | SecretStr | None,
) -> str | None:
    """Return the underlying string from ``SecretStr``/``str``/``None``.

    Blank or whitespace-only strings are normalised to ``None`` so the
    fail-fast check at construct time treats them the same as an unset
    Settings field (mirrors B1 ``_signing.resolve_secret`` discipline).
    """
    if value is None:
        return None
    if isinstance(value, SecretStr):
        value = value.get_secret_value()
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    # Preserve the original (un-stripped) value — Discord's bot token is
    # never whitespace-padded, but the contract is "blank is missing"
    # rather than "trim and use".
    return value


class DiscordRealtimeChannel:
    """Discord channel adapter — conforms to ``RealtimeChannel`` + ``WebhookChannel``.

    The constructor takes secrets via positional arguments OR a
    :class:`cantus.config.Settings` object (constructor args win). All three
    of ``bot_token``, ``public_key``, and ``application_id`` MUST be
    resolvable; a missing value raises :class:`ValueError` with the fixed
    message :data:`_MISSING_SECRET_MESSAGE` that NEVER echoes any supplied
    secret. The ``public_key`` is hex-decoded once at construct time so a
    malformed key fails fast (still with the secret-free message) rather
    than at the first inbound interaction.
    """

    def __init__(
        self,
        bot_token: str | SecretStr | None = None,
        public_key: str | SecretStr | None = None,
        application_id: str | None = None,
        *,
        intents: int = DEFAULT_INTENTS,
        queue_maxlen: int | None = None,
        settings: Settings | None = None,
    ) -> None:
        effective_settings = settings if settings is not None else Settings()

        resolved_bot_token = _coerce_secret(bot_token) or _coerce_secret(
            effective_settings.channel_discord_bot_token
        )
        resolved_public_key = _coerce_secret(public_key) or _coerce_secret(
            effective_settings.channel_discord_public_key
        )
        resolved_application_id = _coerce_secret(
            application_id
        ) or _coerce_secret(effective_settings.channel_discord_application_id)

        if (
            resolved_bot_token is None
            or resolved_public_key is None
            or resolved_application_id is None
        ):
            raise ValueError(_MISSING_SECRET_MESSAGE)

        try:
            public_key_bytes = bytes.fromhex(resolved_public_key)
        except (ValueError, binascii.Error) as exc:
            # Re-raise with the fixed message — the bad hex value MUST NOT
            # appear in the error so accidental log captures of the
            # ValueError don't leak the (possibly partially correct) key.
            raise ValueError(_MISSING_SECRET_MESSAGE) from exc

        self._bot_token: str = resolved_bot_token
        self._public_key_bytes: bytes = public_key_bytes
        self._application_id: str = resolved_application_id
        self._intents: int = intents
        self._queue: deque[dict[str, Any]] = deque(maxlen=queue_maxlen)
        self._queue_maxlen: int | None = queue_maxlen
        self._app: FastAPI | None = None
        self._gateway: GatewayClient | None = None
        self.last_error: BaseException | None = None

    # ----- RealtimeChannel surface ----------------------------------------

    async def connect(self) -> None:
        """Open the long-lived Discord Gateway WebSocket session.

        Wraps :class:`GatewayClient`: every received Discord DISPATCH frame
        is pushed onto the channel's internal ``deque`` via ``on_event``,
        which makes :meth:`receive` thread-free (the FastAPI lifespan owns
        the coroutine that fills the queue). On exit, ``self.last_error``
        mirrors the gateway's ``last_error`` so operators can inspect why
        the connection stopped without reaching into the internal client.
        """
        self._gateway = GatewayClient()
        try:
            await self._gateway.start(
                bot_token=self._bot_token,
                intents=self._intents,
                on_event=self._queue.append,
            )
        finally:
            if self._gateway is not None:
                self.last_error = self._gateway.last_error

    async def disconnect(self) -> None:
        """Close the Gateway session if one was opened."""
        if self._gateway is not None:
            await self._gateway.stop()

    # ----- WebhookChannel surface ----------------------------------------

    def mount(self, app: FastAPI) -> None:
        """Register ``POST /channels/discord/interactions`` on the FastAPI app.

        The handler reads the raw request body, verifies the Ed25519
        signature over ``timestamp + body``, and on success either:

        * Returns ``{"type": 1}`` (PONG) for Discord's Ping (type 1)
          interaction without enqueuing — Discord's verification probe is
          stateless and should never reach application code.
        * Returns ``{"type": 5}`` (DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE)
          for every other interaction type, with the parsed payload pushed
          onto the channel's queue for :meth:`receive` consumers.

        On any verification failure the handler responds with HTTP 401 and
        the byte-identical body ``{"detail":"Authentication required"}``.
        We use ``JSONResponse`` rather than ``HTTPException`` so FastAPI's
        exception handler does not rewrap the body (which would let the
        framework's exception-detail formatter shape leak information
        about the failure mode).
        """
        self._app = app

        public_key_bytes = self._public_key_bytes
        queue = self._queue

        async def _handler(request: Request) -> JSONResponse:
            body = await request.body()
            sig = request.headers.get(SIGNATURE_HEADER)
            ts = request.headers.get(TIMESTAMP_HEADER)
            if sig is None or ts is None:
                return JSONResponse(
                    {"detail": _AUTH_REQUIRED_DETAIL}, status_code=401
                )
            try:
                signature_bytes = bytes.fromhex(sig)
            except (ValueError, binascii.Error):
                return JSONResponse(
                    {"detail": _AUTH_REQUIRED_DETAIL}, status_code=401
                )
            try:
                verify_ed25519(
                    public_key_bytes,
                    ts.encode("utf-8") + body,
                    signature_bytes,
                )
            except DiscordSignatureError:
                return JSONResponse(
                    {"detail": _AUTH_REQUIRED_DETAIL}, status_code=401
                )

            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                # Malformed JSON with a valid signature is highly unusual
                # (Discord always sends valid JSON) but we still refuse to
                # leak the parse error. 401 is the safe collapse.
                return JSONResponse(
                    {"detail": _AUTH_REQUIRED_DETAIL}, status_code=401
                )

            if isinstance(payload, dict) and payload.get("type") == 1:
                # Discord Ping — respond with PONG without enqueuing.
                return JSONResponse({"type": 1})

            if (
                self._queue_maxlen is not None
                and len(queue) >= self._queue_maxlen
            ):
                logger.warning(
                    "DiscordRealtimeChannel queue at maxlen=%d; "
                    "dropped oldest event",
                    self._queue_maxlen,
                )
            queue.append(payload)
            return JSONResponse({"type": 5})

        app.add_api_route(
            path=_INTERACTIONS_ROUTE,
            endpoint=_handler,
            methods=["POST"],
            name="discord_interactions",
            summary="Discord interactions HTTP receiver",
        )

    # ----- Channel surface ------------------------------------------------

    def receive(self) -> dict[str, Any]:
        if not self._queue:
            raise IndexError("DiscordRealtimeChannel queue is empty")
        return self._queue.popleft()

    async def send(self, message: dict[str, Any]) -> None:
        """Route the outbound ``message`` by shape — interaction or channel message.

        * ``"interaction" in message`` → POST to ``/interactions/{id}/{token}/callback``
          with NO Authorization header (Discord uses the interaction token).
        * ``"channel_id" in message`` → POST to ``/channels/{channel_id}/messages``
          with ``Authorization: Bot {bot_token}``.

        Neither key → ``ValueError`` carrying the literal substring
        ``"must carry 'interaction' or 'channel_id'"``. 4xx/5xx responses
        raise :class:`ChannelSendError` whose attributes contain the
        status code, the first 200 bytes of the response body, and
        ``"discord"``; the bot_token never appears in any attribute or
        ``str()`` form because :class:`ChannelSendError` only stores the
        three caller-supplied fields.
        """
        if "interaction" in message:
            interaction = message["interaction"]
            url = (
                f"{_DISCORD_API_BASE}/interactions/"
                f"{interaction['id']}/{interaction['token']}/callback"
            )
            headers: dict[str, str] = {}
        elif "channel_id" in message:
            url = (
                f"{_DISCORD_API_BASE}/channels/"
                f"{message['channel_id']}/messages"
            )
            headers = {"Authorization": f"Bot {self._bot_token}"}
        else:
            raise ValueError(
                "DiscordRealtimeChannel.send: message must carry "
                "'interaction' or 'channel_id'"
            )

        if self._app is None:
            raise RuntimeError(
                "DiscordRealtimeChannel.send requires mount(app) to have been "
                "called and app.state.http_client populated by the FastAPI "
                "lifespan."
            )
        client = self._app.state.http_client
        response = await client.post(
            url,
            json=message.get("data", {}),
            headers=headers,
        )
        if 400 <= response.status_code < 600:
            raise ChannelSendError(
                status_code=response.status_code,
                body_excerpt=response.text[:_BODY_EXCERPT_LIMIT],
                provider="discord",
            )


__all__ = [
    "DEFAULT_INTENTS",
    "DiscordRealtimeChannel",
    "DiscordSignatureError",
]

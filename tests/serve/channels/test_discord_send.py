"""Tests for ``DiscordRealtimeChannel.send()`` outbound dispatch.

Covers Task 5.4 + 5.5:

* ``send({"channel_id": ...})`` POSTs to ``/channels/{id}/messages`` with
  ``Authorization: Bot <token>``.
* ``send({"interaction": {...}})`` POSTs to ``/interactions/{id}/{token}/callback``
  with NO Authorization header (Discord's interaction-callback contract).
* Missing routing key raises ``ValueError`` with the literal substring
  ``"must carry 'interaction' or 'channel_id'"``.
* 4xx response raises ``ChannelSendError`` carrying the exact body excerpt,
  ``provider == "discord"`` and a string form free of the bot_token sentinel.
* ``send()`` before ``mount()`` raises ``RuntimeError``.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from fastapi import FastAPI


VALID_PUBLIC_KEY_HEX = "ab" * 32
BOT_TOKEN_SENTINEL = "Bot-XYZ-secret-sentinel"
APPLICATION_ID = "app_123"


def _build_mounted_channel() -> tuple["object", FastAPI, httpx.AsyncClient]:
    """Build a Discord channel, mount it on an app, attach an http client.

    Tests skip the FastAPI lifespan; ``send()`` only needs
    ``app.state.http_client`` to be a working ``httpx.AsyncClient``.
    """
    from cantus.serve.channels.discord import DiscordRealtimeChannel

    ch = DiscordRealtimeChannel(
        bot_token=BOT_TOKEN_SENTINEL,
        public_key=VALID_PUBLIC_KEY_HEX,
        application_id=APPLICATION_ID,
    )
    app = FastAPI()
    ch.mount(app)
    http_client = httpx.AsyncClient(timeout=10.0)
    app.state.http_client = http_client
    return ch, app, http_client


# --- 5.4 channel_id routing -----------------------------------------------


@pytest.mark.anyio("asyncio")
async def test_send_channel_message_routes_by_channel_id() -> None:
    ch, _, http_client = _build_mounted_channel()
    try:
        with respx.mock(base_url="https://discord.com") as rmock:
            route = rmock.post("/api/v10/channels/12345/messages").mock(
                return_value=httpx.Response(200, json={"id": "msg_1"})
            )
            await ch.send(
                {"channel_id": "12345", "data": {"content": "hi"}}
            )
            assert route.called
            sent = route.calls[0].request
            assert sent.headers["authorization"].startswith("Bot ")
            assert sent.headers["authorization"] == f"Bot {BOT_TOKEN_SENTINEL}"
            assert json.loads(sent.content) == {"content": "hi"}
    finally:
        await http_client.aclose()


# --- 5.4 interaction block routing ----------------------------------------


@pytest.mark.anyio("asyncio")
async def test_send_interaction_callback_routes_by_interaction_block() -> None:
    ch, _, http_client = _build_mounted_channel()
    try:
        with respx.mock(base_url="https://discord.com") as rmock:
            route = rmock.post("/api/v10/interactions/i1/tk1/callback").mock(
                return_value=httpx.Response(200, json={})
            )
            await ch.send(
                {
                    "interaction": {"id": "i1", "token": "tk1"},
                    "data": {"type": 4, "data": {"content": "pong"}},
                }
            )
            assert route.called
    finally:
        await http_client.aclose()


# --- 5.4 missing routing key ---------------------------------------------


@pytest.mark.anyio("asyncio")
async def test_send_missing_routing_key_raises_value_error() -> None:
    ch, _, http_client = _build_mounted_channel()
    try:
        with pytest.raises(ValueError) as exc_info:
            await ch.send({"data": {"content": "orphan"}})
        assert "must carry 'interaction' or 'channel_id'" in str(exc_info.value)
    finally:
        await http_client.aclose()


# --- 5.5 ChannelSendError on 4xx, no token leak --------------------------


@pytest.mark.anyio("asyncio")
async def test_send_4xx_raises_channelsenderror_no_token_leak() -> None:
    from cantus.serve.channels._errors import ChannelSendError

    ch, _, http_client = _build_mounted_channel()
    discord_error_body = '{"message":"Missing Permissions","code":50013}'
    try:
        with respx.mock(base_url="https://discord.com") as rmock:
            rmock.post("/api/v10/channels/12345/messages").mock(
                return_value=httpx.Response(403, text=discord_error_body)
            )
            with pytest.raises(ChannelSendError) as exc_info:
                await ch.send({"channel_id": "12345", "data": {}})
            err = exc_info.value
            assert err.status_code == 403
            assert err.provider == "discord"
            assert err.body_excerpt == discord_error_body
            assert BOT_TOKEN_SENTINEL not in str(err)
            assert BOT_TOKEN_SENTINEL not in repr(err)
    finally:
        await http_client.aclose()


# --- 5.4 send-before-mount fail-fast --------------------------------------


@pytest.mark.anyio("asyncio")
async def test_send_before_mount_raises() -> None:
    """Calling send() without first calling mount() raises RuntimeError."""
    from cantus.serve.channels.discord import DiscordRealtimeChannel

    ch = DiscordRealtimeChannel(
        bot_token=BOT_TOKEN_SENTINEL,
        public_key=VALID_PUBLIC_KEY_HEX,
        application_id=APPLICATION_ID,
    )
    with pytest.raises(RuntimeError) as exc_info:
        await ch.send({"channel_id": "12345", "data": {"content": "x"}})
    # No bot_token leakage in the RuntimeError message either.
    assert BOT_TOKEN_SENTINEL not in str(exc_info.value)

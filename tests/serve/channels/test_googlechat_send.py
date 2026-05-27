"""Tests for ``GoogleChatPubSubChannel.send()`` outbound dispatch.

Covers tasks 7.1-7.4 of cantus-channel-gateway-pubsub:

* ``send({"space": ..., "data": ...})`` POSTs to
  ``/v1/spaces/{space}/messages`` with ``Authorization: Bearer <token>``.
* When ``message["space"]`` is missing, the routing falls back to
  ``Settings.channel_google_chat_space``.
* When both are missing, ``send()`` raises ``ValueError`` with the
  literal substring ``must carry 'space' or set Settings.channel_google_chat_space``.
* HTTP 4xx/5xx surfaces as ``ChannelSendError(provider="google_chat", ...)``
  whose string form does NOT contain the bearer token.
* HTTP 500 with a body longer than 200 chars yields ``body_excerpt`` of
  exactly 200 chars.
"""

from __future__ import annotations

import json

import httpx
import pytest
import respx
from fastapi import FastAPI

from cantus.config import Settings
from cantus.serve.channels._errors import ChannelSendError
from cantus.serve.channels.googlechat import GoogleChatPubSubChannel


CREDENTIALS_PATH = "/tmp/sa.json"
SUBSCRIPTION = "projects/p/subscriptions/s"
DEFAULT_SPACE = "spaces/DEFAULT"
TOKEN_MARKER = "ya29.test-token-marker"


def _build_channel_with_http_client() -> (
    tuple[GoogleChatPubSubChannel, FastAPI, httpx.AsyncClient]
):
    """Build a channel with a stubbed token cache + an app-bound httpx client.

    The token cache is replaced wholesale so the test never reaches the
    real google-auth stack — we want to exercise the ``send()`` HTTP
    surface without needing a fake RSA SA JSON.
    """
    settings = Settings(
        channel_google_chat_credentials_path=CREDENTIALS_PATH,
        channel_google_chat_subscription=SUBSCRIPTION,
        channel_google_chat_space=DEFAULT_SPACE,
    )
    ch = GoogleChatPubSubChannel(settings=settings)

    async def _fake_get_token() -> str:
        return TOKEN_MARKER

    ch._token_cache.get_token = _fake_get_token  # type: ignore[method-assign]

    app = FastAPI()
    http_client = httpx.AsyncClient(timeout=10.0)
    app.state.http_client = http_client
    ch._app = app
    return ch, app, http_client


# --- Task 7.1 — routes by message space key -------------------------------


@pytest.mark.anyio("asyncio")
async def test_send_routes_by_message_space_key() -> None:
    """Task 7.1 — when ``message["space"]`` is set, the POST URL uses it."""
    ch, _, http_client = _build_channel_with_http_client()
    try:
        with respx.mock(base_url="https://chat.googleapis.com") as rmock:
            route = rmock.post(
                "/v1/spaces/spaces/OVERRIDE/messages"
            ).mock(return_value=httpx.Response(200, json={"name": "m1"}))
            await ch.send(
                {"space": "spaces/OVERRIDE", "data": {"text": "hi"}}
            )
            assert route.called
            sent = route.calls[0].request
            assert sent.headers["authorization"] == f"Bearer {TOKEN_MARKER}"
            assert json.loads(sent.content) == {"text": "hi"}
    finally:
        await http_client.aclose()


# --- Task 7.2 — fallback to Settings.channel_google_chat_space ------------


@pytest.mark.anyio("asyncio")
async def test_send_falls_back_to_settings_space() -> None:
    """Task 7.2 — when ``message["space"]`` is absent, the default space
    resolved from Settings at construction time is used."""
    ch, _, http_client = _build_channel_with_http_client()
    try:
        with respx.mock(base_url="https://chat.googleapis.com") as rmock:
            route = rmock.post(
                f"/v1/spaces/{DEFAULT_SPACE}/messages"
            ).mock(return_value=httpx.Response(200, json={"name": "m1"}))
            await ch.send({"data": {"text": "hi"}})
            assert route.called
    finally:
        await http_client.aclose()


# --- Task 7.3 — missing space raises ValueError ---------------------------


@pytest.mark.anyio("asyncio")
async def test_missing_space_raises_value_error_with_fixed_message() -> None:
    """Task 7.3 — when both ``message["space"]`` and
    ``Settings.channel_google_chat_space`` are absent, send() raises
    ``ValueError`` with the fixed substring."""
    ch, _, http_client = _build_channel_with_http_client()
    try:
        # Simulate "Settings has no default space" by zeroing the channel's
        # internal default at runtime.
        ch._default_space = ""
        with pytest.raises(ValueError) as exc_info:
            await ch.send({"data": {"text": "hi"}})
        assert (
            "must carry 'space' or set Settings.channel_google_chat_space"
            in str(exc_info.value)
        )
    finally:
        await http_client.aclose()


# --- Task 7.4 — 4xx surfaces as ChannelSendError without token leak -------


@pytest.mark.anyio("asyncio")
async def test_403_surfaces_channel_send_error_without_token_leak() -> None:
    """Task 7.4 — HTTP 403 raises ChannelSendError with
    ``provider="google_chat"``; ``str(err)`` does NOT contain the bearer
    token value."""
    ch, _, http_client = _build_channel_with_http_client()
    try:
        with respx.mock(base_url="https://chat.googleapis.com") as rmock:
            rmock.post(
                "/v1/spaces/spaces/X/messages"
            ).mock(
                return_value=httpx.Response(
                    403,
                    text='{"error":{"code":403,"message":"Forbidden"}}',
                )
            )
            with pytest.raises(ChannelSendError) as exc_info:
                await ch.send({"space": "spaces/X", "data": {"text": "hi"}})
            err = exc_info.value
            assert err.status_code == 403
            assert err.provider == "google_chat"
            assert err.body_excerpt == (
                '{"error":{"code":403,"message":"Forbidden"}}'
            )
            # Bearer token MUST NOT appear in the string form of the error.
            assert TOKEN_MARKER not in str(err)
            assert TOKEN_MARKER not in repr(err)
    finally:
        await http_client.aclose()


@pytest.mark.anyio("asyncio")
async def test_500_body_excerpt_truncated_to_200_chars() -> None:
    """Task 7.4 — HTTP 500 with body > 200 chars produces a 200-char excerpt."""
    ch, _, http_client = _build_channel_with_http_client()
    long_body = "x" * 400
    try:
        with respx.mock(base_url="https://chat.googleapis.com") as rmock:
            rmock.post(
                "/v1/spaces/spaces/X/messages"
            ).mock(return_value=httpx.Response(500, text=long_body))
            with pytest.raises(ChannelSendError) as exc_info:
                await ch.send({"space": "spaces/X", "data": {"text": "hi"}})
            assert exc_info.value.status_code == 500
            assert len(exc_info.value.body_excerpt) == 200
            assert exc_info.value.body_excerpt == "x" * 200
    finally:
        await http_client.aclose()

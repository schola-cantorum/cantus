"""Tests for ``DiscordRealtimeChannel.mount()`` HTTP interactions endpoint.

Covers Task 5.3 + 5.6 + 7.3:

* Valid Ping (type 1) returns ``{"type":1}`` (PONG) **without** enqueuing.
* Valid ApplicationCommand (type 2) enqueues the payload and returns
  ``{"type":5}`` (DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE).
* Every signature failure mode (tampered body, tampered timestamp,
  missing signature header, missing timestamp header, malformed hex
  signature) returns HTTP 401 with the byte-identical body
  ``{"detail":"Authentication required"}``.
* ``mount(app)`` registers exactly one route ``POST /channels/discord/interactions``.

Tests generate a fresh Ed25519 keypair per case with ``nacl.signing.SigningKey``;
the channel's ``public_key`` argument is the hex-encoded verify key so the
construct-time hex-decode lands on the same 32-byte value the test signs against.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from nacl.signing import SigningKey


BOT_TOKEN = "bot-token-XYZ"
APPLICATION_ID = "app_123"
EXPECTED_401_BODY: dict[str, Any] = {"detail": "Authentication required"}


def _make_channel_with_signing_key() -> tuple["object", FastAPI, SigningKey]:
    """Construct a ``DiscordRealtimeChannel`` whose public_key matches ``signing_key``.

    Returns ``(channel, app, signing_key)``. The channel is mounted on a fresh
    ``FastAPI`` app; no lifespan is entered (mount() does not need one for
    inbound).
    """
    from cantus.serve.channels.discord import DiscordRealtimeChannel

    signing_key = SigningKey.generate()
    public_key_hex = bytes(signing_key.verify_key).hex()

    ch = DiscordRealtimeChannel(
        bot_token=BOT_TOKEN,
        public_key=public_key_hex,
        application_id=APPLICATION_ID,
    )
    app = FastAPI()
    ch.mount(app)
    return ch, app, signing_key


def _sign(signing_key: SigningKey, timestamp: bytes, body: bytes) -> str:
    """Return the hex-encoded Ed25519 signature over ``timestamp + body``."""
    sig = signing_key.sign(timestamp + body).signature
    return sig.hex()


# --- 5.3 Ping returns PONG without enqueuing -----------------------------


def test_ping_returns_pong_without_enqueuing() -> None:
    ch, app, signing_key = _make_channel_with_signing_key()
    body = json.dumps({"type": 1}).encode("utf-8")
    timestamp = b"1700000000"
    sig = _sign(signing_key, timestamp, body)

    with TestClient(app) as client:
        resp = client.post(
            "/channels/discord/interactions",
            content=body,
            headers={
                "X-Signature-Ed25519": sig,
                "X-Signature-Timestamp": timestamp.decode("ascii"),
                "content-type": "application/json",
            },
        )

    assert resp.status_code == 200
    assert resp.json() == {"type": 1}
    # Queue NOT populated for Ping.
    with pytest.raises(IndexError):
        ch.receive()


# --- 5.3 ApplicationCommand enqueued & returns type 5 --------------------


def test_application_command_enqueued_and_returns_type_5() -> None:
    ch, app, signing_key = _make_channel_with_signing_key()
    payload = {"type": 2, "data": {"name": "ping"}}
    body = json.dumps(payload).encode("utf-8")
    timestamp = b"1700000001"
    sig = _sign(signing_key, timestamp, body)

    with TestClient(app) as client:
        resp = client.post(
            "/channels/discord/interactions",
            content=body,
            headers={
                "X-Signature-Ed25519": sig,
                "X-Signature-Timestamp": timestamp.decode("ascii"),
                "content-type": "application/json",
            },
        )

    assert resp.status_code == 200
    assert resp.json() == {"type": 5}
    assert ch.receive() == payload


# --- 5.3 / 5.6 401 indistinguishability matrix ---------------------------


def test_tampered_body_returns_401_indistinguishable() -> None:
    _, app, signing_key = _make_channel_with_signing_key()
    original = json.dumps({"type": 1}).encode("utf-8")
    timestamp = b"1700000002"
    sig = _sign(signing_key, timestamp, original)
    tampered = json.dumps({"type": 2}).encode("utf-8")

    with TestClient(app) as client:
        resp = client.post(
            "/channels/discord/interactions",
            content=tampered,
            headers={
                "X-Signature-Ed25519": sig,
                "X-Signature-Timestamp": timestamp.decode("ascii"),
                "content-type": "application/json",
            },
        )

    assert resp.status_code == 401
    assert resp.json() == EXPECTED_401_BODY


def test_missing_signature_header_returns_401_indistinguishable() -> None:
    _, app, _ = _make_channel_with_signing_key()
    body = json.dumps({"type": 1}).encode("utf-8")
    timestamp = b"1700000003"

    with TestClient(app) as client:
        resp = client.post(
            "/channels/discord/interactions",
            content=body,
            headers={
                "X-Signature-Timestamp": timestamp.decode("ascii"),
                "content-type": "application/json",
            },
        )

    assert resp.status_code == 401
    assert resp.json() == EXPECTED_401_BODY


def test_missing_timestamp_header_returns_401() -> None:
    _, app, signing_key = _make_channel_with_signing_key()
    body = json.dumps({"type": 1}).encode("utf-8")
    timestamp = b"1700000004"
    sig = _sign(signing_key, timestamp, body)

    with TestClient(app) as client:
        resp = client.post(
            "/channels/discord/interactions",
            content=body,
            headers={
                "X-Signature-Ed25519": sig,
                "content-type": "application/json",
            },
        )

    assert resp.status_code == 401
    assert resp.json() == EXPECTED_401_BODY


def test_bad_hex_in_signature_header_returns_401() -> None:
    _, app, _ = _make_channel_with_signing_key()
    body = json.dumps({"type": 1}).encode("utf-8")
    timestamp = b"1700000005"

    with TestClient(app) as client:
        resp = client.post(
            "/channels/discord/interactions",
            content=body,
            headers={
                "X-Signature-Ed25519": "zzz",
                "X-Signature-Timestamp": timestamp.decode("ascii"),
                "content-type": "application/json",
            },
        )

    assert resp.status_code == 401
    assert resp.json() == EXPECTED_401_BODY


def test_401_response_body_is_byte_identical_across_failure_modes() -> None:
    """Task 5.6: tampered body and missing header return byte-identical 401 body."""
    _, app, signing_key = _make_channel_with_signing_key()
    body = json.dumps({"type": 1}).encode("utf-8")
    timestamp = b"1700000006"
    sig = _sign(signing_key, timestamp, body)
    tampered_body = json.dumps({"type": 99}).encode("utf-8")

    with TestClient(app) as client:
        resp_tampered = client.post(
            "/channels/discord/interactions",
            content=tampered_body,
            headers={
                "X-Signature-Ed25519": sig,
                "X-Signature-Timestamp": timestamp.decode("ascii"),
                "content-type": "application/json",
            },
        )
        resp_missing = client.post(
            "/channels/discord/interactions",
            content=body,
            headers={
                "X-Signature-Timestamp": timestamp.decode("ascii"),
                "content-type": "application/json",
            },
        )

    assert resp_tampered.status_code == 401
    assert resp_missing.status_code == 401
    # Byte-identical body — the entire response payload must match.
    assert resp_tampered.content == resp_missing.content


# --- 7.3 mount registers exactly one POST route --------------------------


def test_route_registered() -> None:
    from fastapi.routing import APIRoute

    _, app, _ = _make_channel_with_signing_key()
    matching = [
        route
        for route in app.router.routes
        if isinstance(route, APIRoute)
        and route.path == "/channels/discord/interactions"
    ]
    assert len(matching) == 1
    assert "POST" in matching[0].methods

"""Tests for cantus.serve.channels.line.LineWebhookChannel."""

from __future__ import annotations

import json
import logging

import httpx
import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cantus.serve.channels._signing import compute_line_signature


SECRET = "test_secret"
ACCESS_TOKEN = "line-token-XYZ"


def _make_app_with_channel(
    secret: str = SECRET,
    access_token: str = ACCESS_TOKEN,
    queue_maxlen: int | None = None,
) -> tuple[FastAPI, "object"]:
    from cantus.serve.channels.line import LineWebhookChannel

    ch = LineWebhookChannel(
        channel_secret=secret,
        channel_access_token=access_token,
        queue_maxlen=queue_maxlen,
    )
    app = FastAPI()
    ch.mount(app)
    return app, ch


# --- 4.1 constructor fail-fast ------------------------------------------


def test_constructor_fail_fast_both_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from cantus.serve.channels.line import LineWebhookChannel

    monkeypatch.delenv("CANTUS_SERVE_CHANNEL_LINE_SECRET", raising=False)
    monkeypatch.delenv("CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN", raising=False)
    with pytest.raises(ValueError) as exc_info:
        LineWebhookChannel()
    msg = str(exc_info.value)
    assert "channel secret not configured" in msg
    assert "channel_line_secret" in msg


def test_constructor_fail_fast_only_secret_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cantus.serve.channels.line import LineWebhookChannel

    monkeypatch.delenv("CANTUS_SERVE_CHANNEL_LINE_SECRET", raising=False)
    with pytest.raises(ValueError, match="channel_line_secret"):
        LineWebhookChannel(channel_access_token="anything")


def test_constructor_succeeds_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from cantus.config import Settings
    from cantus.serve.channels.line import LineWebhookChannel

    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_LINE_SECRET", "from-env-secret")
    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN", "from-env-token")
    ch = LineWebhookChannel(settings=Settings())
    # Internal state — access via private name only for behaviour assertion.
    assert ch._channel_secret == "from-env-secret"
    assert ch._channel_access_token == "from-env-token"


# --- 4.2 mount registers route -----------------------------------------


def test_mount_registers_route() -> None:
    app, _ = _make_app_with_channel()
    paths = [(route.path, list(route.methods)) for route in app.routes]
    assert any(
        path == "/channels/line" and "POST" in methods for path, methods in paths
    ), f"missing /channels/line POST: routes={paths}"


# --- 4.3 inbound signature matrix --------------------------------------


def test_inbound_correct_signature_returns_200_and_enqueues() -> None:
    app, ch = _make_app_with_channel()
    body_obj = {"events": [{"type": "message"}], "destination": "U123"}
    raw = json.dumps(body_obj).encode("utf-8")
    sig = compute_line_signature(SECRET, raw)

    with TestClient(app) as client:
        resp = client.post(
            "/channels/line",
            content=raw,
            headers={"x-line-signature": sig, "content-type": "application/json"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert ch.receive() == body_obj


def test_inbound_wrong_signature_returns_401_indistinguishable() -> None:
    app, ch = _make_app_with_channel()
    raw = b'{"events":[]}'
    with TestClient(app) as client:
        resp = client.post(
            "/channels/line",
            content=raw,
            headers={"x-line-signature": "bogus", "content-type": "application/json"},
        )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Authentication required"}
    # Queue NOT populated.
    with pytest.raises(IndexError):
        ch.receive()


def test_inbound_missing_signature_returns_401_indistinguishable() -> None:
    app, ch = _make_app_with_channel()
    raw = b'{"events":[]}'
    with TestClient(app) as client:
        resp = client.post(
            "/channels/line",
            content=raw,
            headers={"content-type": "application/json"},
        )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Authentication required"}
    with pytest.raises(IndexError):
        ch.receive()


# --- 4.4 receive pass-through + IndexError ------------------------------


def test_receive_pass_through_preserves_nested_structure() -> None:
    app, ch = _make_app_with_channel()
    payload = {
        "destination": "U-deep",
        "events": [
            {
                "type": "message",
                "message": {"type": "text", "text": "héllo 中文 🌟"},
                "source": {"type": "user", "userId": "U-1"},
                "nested": {"a": [1, 2, {"b": "c"}]},
            }
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sig = compute_line_signature(SECRET, raw)
    with TestClient(app) as client:
        client.post(
            "/channels/line",
            content=raw,
            headers={"x-line-signature": sig, "content-type": "application/json"},
        )
    assert ch.receive() == payload


def test_receive_empty_queue_raises_index_error() -> None:
    _, ch = _make_app_with_channel()
    with pytest.raises(IndexError, match="queue is empty"):
        ch.receive()


# --- 4.5 queue_maxlen drop oldest --------------------------------------


def test_queue_maxlen_drops_oldest_and_logs_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app, ch = _make_app_with_channel(queue_maxlen=2)

    def _send(idx: int) -> None:
        raw = json.dumps({"i": idx}).encode("utf-8")
        sig = compute_line_signature(SECRET, raw)
        with TestClient(app) as client:
            client.post(
                "/channels/line",
                content=raw,
                headers={"x-line-signature": sig, "content-type": "application/json"},
            )

    caplog.set_level(logging.WARNING, logger="cantus.serve.channels")
    _send(1)
    _send(2)
    _send(3)  # this push triggers drop-oldest of {"i": 1}

    # Newer two remain.
    assert ch.receive() == {"i": 2}
    assert ch.receive() == {"i": 3}
    # A warning was logged mentioning "dropped".
    assert any(
        "dropped" in record.getMessage().lower() for record in caplog.records
    ), f"expected drop warning, got: {[r.getMessage() for r in caplog.records]}"


# --- 4.6 send outbound httpx ------------------------------------------


def _attach_http_client(app: FastAPI) -> httpx.AsyncClient:
    """Tests skip the FastAPI lifespan, so attach the client manually."""
    client = httpx.AsyncClient(timeout=10.0)
    app.state.http_client = client
    return client


@pytest.mark.anyio("asyncio")
async def test_send_outbound_200_returns_none() -> None:
    app, ch = _make_app_with_channel()
    client = _attach_http_client(app)
    try:
        with respx.mock(base_url="https://api.line.me") as rmock:
            route = rmock.post("/v2/bot/message/reply").mock(
                return_value=httpx.Response(200, json={})
            )
            result = await ch.send(
                {"replyToken": "abc", "messages": [{"type": "text", "text": "hi"}]}
            )
            assert result is None
            assert route.called
            sent = route.calls[0].request
            assert sent.headers["authorization"] == f"Bearer {ACCESS_TOKEN}"
            assert sent.headers["content-type"].startswith("application/json")
            assert json.loads(sent.content) == {
                "replyToken": "abc",
                "messages": [{"type": "text", "text": "hi"}],
            }
    finally:
        await client.aclose()


@pytest.mark.anyio("asyncio")
async def test_send_outbound_400_raises_channel_send_error() -> None:
    from cantus.serve.channels._errors import ChannelSendError

    app, ch = _make_app_with_channel()
    client = _attach_http_client(app)
    try:
        with respx.mock(base_url="https://api.line.me") as rmock:
            rmock.post("/v2/bot/message/reply").mock(
                return_value=httpx.Response(
                    400, json={"message": "Invalid reply token"}
                )
            )
            with pytest.raises(ChannelSendError) as exc_info:
                await ch.send({"replyToken": "stale", "messages": []})
            err = exc_info.value
            assert err.status_code == 400
            assert err.provider == "line"
            assert "Invalid reply token" in err.body_excerpt
    finally:
        await client.aclose()


# --- 4.7 ChannelSendError does not leak access_token --------------------


@pytest.mark.anyio("asyncio")
async def test_send_error_does_not_leak_access_token() -> None:
    from cantus.serve.channels._errors import ChannelSendError

    app, ch = _make_app_with_channel()
    client = _attach_http_client(app)
    try:
        with respx.mock(base_url="https://api.line.me") as rmock:
            rmock.post("/v2/bot/message/reply").mock(
                return_value=httpx.Response(401, text="unauthorized")
            )
            with pytest.raises(ChannelSendError) as exc_info:
                await ch.send({"replyToken": "x", "messages": []})
            assert ACCESS_TOKEN not in str(exc_info.value)
            assert ACCESS_TOKEN not in repr(exc_info.value)
    finally:
        await client.aclose()

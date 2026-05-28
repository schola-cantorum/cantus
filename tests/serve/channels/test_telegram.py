"""Tests for cantus.serve.channels.telegram.TelegramWebhookChannel."""

from __future__ import annotations

import json
import logging

import httpx
import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient


SECRET_TOKEN = "tg-secret"
BOT_TOKEN = "123:abcdefghijklmnopqrstuvwxyz"


def _make_app_with_channel(
    secret_token: str = SECRET_TOKEN,
    bot_token: str = BOT_TOKEN,
    queue_maxlen: int | None = None,
) -> tuple[FastAPI, "object"]:
    from cantus.serve.channels.telegram import TelegramWebhookChannel

    ch = TelegramWebhookChannel(
        secret_token=secret_token,
        bot_token=bot_token,
        queue_maxlen=queue_maxlen,
    )
    app = FastAPI()
    ch.mount(app)
    return app, ch


# --- 5.0 constructor format validation (Gate B M1) ---------------------

VALID_BOT_TOKEN = "123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ_-"
VALID_SECRET_TOKEN = "Sample_Secret-Token"


def test_constructor_accepts_valid_bot_token_and_secret_token() -> None:
    from cantus.serve.channels.telegram import TelegramWebhookChannel

    ch = TelegramWebhookChannel(
        secret_token=VALID_SECRET_TOKEN,
        bot_token=VALID_BOT_TOKEN,
    )
    assert ch._secret_token == VALID_SECRET_TOKEN
    assert ch._bot_token == VALID_BOT_TOKEN


@pytest.mark.parametrize(
    "bad_bot_token",
    [
        "not-a-valid-token",
        "abc:abcdefghijklmnopqrst",
        "123:short",
        "123456789:" + "A" * 250,
    ],
    ids=[
        "no_digit_prefix_no_colon",
        "non_digit_prefix",
        "suffix_shorter_than_twenty",
        "length_over_255",
    ],
)
def test_constructor_rejects_bot_token_format_violation(bad_bot_token: str) -> None:
    from cantus.serve.channels.telegram import TelegramWebhookChannel

    with pytest.raises(ValueError) as exc_info:
        TelegramWebhookChannel(
            secret_token=VALID_SECRET_TOKEN,
            bot_token=bad_bot_token,
        )
    msg = str(exc_info.value)
    assert "telegram bot_token has invalid format" in msg
    assert bad_bot_token not in msg


@pytest.mark.parametrize(
    "bad_secret_token",
    [
        "has spaces",
        "with!special",
        "with#hash",
        "A" * 257,
    ],
    ids=["whitespace", "exclamation", "hash", "length_over_256"],
)
def test_constructor_rejects_secret_token_format_violation(
    bad_secret_token: str,
) -> None:
    from cantus.serve.channels.telegram import TelegramWebhookChannel

    with pytest.raises(ValueError) as exc_info:
        TelegramWebhookChannel(
            secret_token=bad_secret_token,
            bot_token=VALID_BOT_TOKEN,
        )
    msg = str(exc_info.value)
    assert "telegram secret_token has invalid format" in msg
    assert bad_secret_token not in msg


def test_constructor_blank_check_runs_before_format_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank/missing must still produce the original message, not 'invalid format'."""
    from cantus.serve.channels.telegram import TelegramWebhookChannel

    monkeypatch.delenv("CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN", raising=False)
    monkeypatch.delenv("CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(ValueError) as exc_info:
        TelegramWebhookChannel()
    msg = str(exc_info.value)
    assert "channel secret not configured" in msg
    assert "invalid format" not in msg


# --- 5.1 constructor fail-fast ------------------------------------------


def test_constructor_fail_fast_both_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    from cantus.serve.channels.telegram import TelegramWebhookChannel

    monkeypatch.delenv("CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN", raising=False)
    monkeypatch.delenv("CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(ValueError) as exc_info:
        TelegramWebhookChannel()
    msg = str(exc_info.value)
    assert "channel secret not configured" in msg
    assert "channel_telegram_secret_token" in msg


def test_constructor_fail_fast_only_bot_token_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from cantus.serve.channels.telegram import TelegramWebhookChannel

    monkeypatch.delenv("CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(ValueError, match="channel_telegram_bot_token"):
        TelegramWebhookChannel(secret_token="anything")


def test_constructor_succeeds_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from cantus.config import Settings
    from cantus.serve.channels.telegram import TelegramWebhookChannel

    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_TELEGRAM_SECRET_TOKEN", "env-secret-tg")
    monkeypatch.setenv(
        "CANTUS_SERVE_CHANNEL_TELEGRAM_BOT_TOKEN", "999:env-tg-bot-XXXXXXXXXXXXX"
    )
    ch = TelegramWebhookChannel(settings=Settings())
    assert ch._secret_token == "env-secret-tg"
    assert ch._bot_token == "999:env-tg-bot-XXXXXXXXXXXXX"


# --- 5.2 mount registers route -----------------------------------------


def test_mount_registers_route() -> None:
    app, _ = _make_app_with_channel()
    paths = [(route.path, list(route.methods)) for route in app.routes]
    assert any(
        path == "/channels/telegram" and "POST" in methods
        for path, methods in paths
    ), f"missing /channels/telegram POST: routes={paths}"


# --- 5.3 inbound secret_token matrix -----------------------------------


def test_inbound_correct_secret_token_returns_200_and_enqueues() -> None:
    app, ch = _make_app_with_channel()
    payload = {"update_id": 1, "message": {"text": "hi"}}
    with TestClient(app) as client:
        resp = client.post(
            "/channels/telegram",
            json=payload,
            headers={"x-telegram-bot-api-secret-token": SECRET_TOKEN},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert ch.receive() == payload


def test_inbound_wrong_secret_token_returns_401_indistinguishable() -> None:
    app, ch = _make_app_with_channel()
    with TestClient(app) as client:
        resp = client.post(
            "/channels/telegram",
            json={"update_id": 1},
            headers={"x-telegram-bot-api-secret-token": "wrong"},
        )
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Authentication required"}
    with pytest.raises(IndexError):
        ch.receive()


def test_inbound_missing_secret_token_returns_401_indistinguishable() -> None:
    app, ch = _make_app_with_channel()
    with TestClient(app) as client:
        resp = client.post("/channels/telegram", json={"update_id": 1})
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Authentication required"}
    with pytest.raises(IndexError):
        ch.receive()


# --- 5.4 receive pass-through + queue_maxlen ----------------------------


def test_receive_pass_through_and_maxlen(caplog: pytest.LogCaptureFixture) -> None:
    app, ch = _make_app_with_channel(queue_maxlen=2)

    def _post(payload: dict) -> None:
        with TestClient(app) as client:
            client.post(
                "/channels/telegram",
                json=payload,
                headers={"x-telegram-bot-api-secret-token": SECRET_TOKEN},
            )

    caplog.set_level(logging.WARNING, logger="cantus.serve.channels")
    _post({"update_id": 1, "nested": {"a": [1, 2, 3]}})
    _post({"update_id": 2})
    _post({"update_id": 3})

    # Oldest dropped, two newest remain.
    assert ch.receive() == {"update_id": 2}
    assert ch.receive() == {"update_id": 3}
    assert any("dropped" in r.getMessage().lower() for r in caplog.records)


# --- 5.5 send outbound httpx ------------------------------------------


def _attach_http_client(app: FastAPI) -> httpx.AsyncClient:
    client = httpx.AsyncClient(timeout=10.0)
    app.state.http_client = client
    return client


@pytest.mark.anyio("asyncio")
async def test_send_outbound_200_returns_none() -> None:
    app, ch = _make_app_with_channel()
    client = _attach_http_client(app)
    try:
        with respx.mock(base_url="https://api.telegram.org") as rmock:
            route = rmock.post(f"/bot{BOT_TOKEN}/sendMessage").mock(
                return_value=httpx.Response(200, json={"ok": True, "result": {}})
            )
            result = await ch.send({"chat_id": 123, "text": "hi"})
            assert result is None
            assert route.called
            sent = route.calls[0].request
            assert sent.headers["content-type"].startswith("application/json")
            assert json.loads(sent.content) == {"chat_id": 123, "text": "hi"}
    finally:
        await client.aclose()


@pytest.mark.anyio("asyncio")
async def test_send_outbound_403_raises_channel_send_error() -> None:
    from cantus.serve.channels._errors import ChannelSendError

    app, ch = _make_app_with_channel()
    client = _attach_http_client(app)
    try:
        with respx.mock(base_url="https://api.telegram.org") as rmock:
            rmock.post(f"/bot{BOT_TOKEN}/sendMessage").mock(
                return_value=httpx.Response(
                    403,
                    json={
                        "ok": False,
                        "error_code": 403,
                        "description": "bot blocked",
                    },
                )
            )
            with pytest.raises(ChannelSendError) as exc_info:
                await ch.send({"chat_id": 1, "text": "x"})
            err = exc_info.value
            assert err.status_code == 403
            assert err.provider == "telegram"
            assert "bot blocked" in err.body_excerpt
    finally:
        await client.aclose()


# --- 5.6 send error doesn't leak bot_token ----------------------------


@pytest.mark.anyio("asyncio")
async def test_send_error_does_not_leak_bot_token() -> None:
    from cantus.serve.channels._errors import ChannelSendError

    app, ch = _make_app_with_channel()
    client = _attach_http_client(app)
    try:
        with respx.mock(base_url="https://api.telegram.org") as rmock:
            rmock.post(f"/bot{BOT_TOKEN}/sendMessage").mock(
                return_value=httpx.Response(400, text="bad request")
            )
            with pytest.raises(ChannelSendError) as exc_info:
                await ch.send({"chat_id": 1, "text": "x"})
            assert BOT_TOKEN not in str(exc_info.value)
            assert BOT_TOKEN not in repr(exc_info.value)
    finally:
        await client.aclose()

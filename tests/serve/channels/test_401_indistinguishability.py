"""401 response body must be byte-identical across all webhook signature failures.

This locks in the v0.4.1 ``require_auth`` discipline at the webhook gateway:
the body cannot reveal whether the header was missing, malformed, or wrong,
so an external probe cannot enumerate signature material.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cantus.serve.channels._signing import compute_line_signature
from cantus.serve.channels.line import LineWebhookChannel
from cantus.serve.channels.telegram import TelegramWebhookChannel

EXPECTED_BODY: dict[str, Any] = {"detail": "Authentication required"}


def _line_app() -> tuple[FastAPI, str]:
    secret = "indist-line-secret"
    ch = LineWebhookChannel(
        channel_secret=secret, channel_access_token="tok"
    )
    app = FastAPI()
    ch.mount(app)
    return app, secret


def _telegram_app() -> tuple[FastAPI, str]:
    token = "indist-tg-token"
    ch = TelegramWebhookChannel(secret_token=token, bot_token="9:bot")
    app = FastAPI()
    ch.mount(app)
    return app, token


@pytest.mark.parametrize(
    "case",
    [
        "line-missing-header",
        "line-wrong-digest",
        "line-empty-header-value",
        "telegram-missing-header",
        "telegram-wrong-token",
    ],
)
def test_401_response_body_is_byte_identical(case: str) -> None:
    if case.startswith("line"):
        app, secret = _line_app()
        url = "/channels/line"
        raw_body = json.dumps({"events": []}).encode("utf-8")
        headers: dict[str, str] = {"content-type": "application/json"}
        if case == "line-missing-header":
            pass
        elif case == "line-wrong-digest":
            headers["x-line-signature"] = "wrong-digest"
        elif case == "line-empty-header-value":
            headers["x-line-signature"] = ""
        else:
            raise AssertionError(f"unhandled case: {case}")
        with TestClient(app) as client:
            resp = client.post(url, content=raw_body, headers=headers)
    else:
        app, _token = _telegram_app()
        url = "/channels/telegram"
        body = {"update_id": 1}
        headers = {}
        if case == "telegram-missing-header":
            pass
        elif case == "telegram-wrong-token":
            headers["x-telegram-bot-api-secret-token"] = "wrong"
        else:
            raise AssertionError(f"unhandled case: {case}")
        with TestClient(app) as client:
            resp = client.post(url, json=body, headers=headers)

    assert resp.status_code == 401, case
    assert resp.json() == EXPECTED_BODY, case


def test_correct_signature_still_passes_for_baseline() -> None:
    """Sanity: the indistinguishability discipline must not break the happy path."""
    app, secret = _line_app()
    raw = json.dumps({"events": []}).encode("utf-8")
    sig = compute_line_signature(secret, raw)
    with TestClient(app) as client:
        resp = client.post(
            "/channels/line",
            content=raw,
            headers={"x-line-signature": sig, "content-type": "application/json"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

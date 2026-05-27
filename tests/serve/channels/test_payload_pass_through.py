"""Inbound payload must reach receive() byte-for-byte identical to raw JSON.

D7 (design): webhook handlers do NOT normalize / coerce / re-key the platform
payload. The receive() return value deep-equals the parsed JSON of the
inbound POST body.
"""

from __future__ import annotations

import copy
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cantus.serve.channels._signing import compute_line_signature
from cantus.serve.channels.line import LineWebhookChannel
from cantus.serve.channels.telegram import TelegramWebhookChannel


# Representative LINE webhook payload from LINE Messaging API documentation.
_LINE_SAMPLE = {
    "destination": "U-destination-id",
    "events": [
        {
            "type": "message",
            "mode": "active",
            "timestamp": 1735690000000,
            "source": {"type": "user", "userId": "U-1234567890abcdef"},
            "webhookEventId": "01EX12ABCDEFG",
            "deliveryContext": {"isRedelivery": False},
            "message": {
                "id": "987654321",
                "type": "text",
                "text": "héllo 中文 🌟",
                "quoteToken": "q-token-xyz",
            },
            "replyToken": "reply-token-here",
        }
    ],
}


# Representative Telegram update payload from Bot API documentation.
_TELEGRAM_SAMPLE = {
    "update_id": 999666333,
    "message": {
        "message_id": 42,
        "from": {
            "id": 11111,
            "is_bot": False,
            "first_name": "Tester",
            "language_code": "zh-Hant",
        },
        "chat": {"id": 11111, "first_name": "Tester", "type": "private"},
        "date": 1735690000,
        "text": "/start 中文 🌟",
        "entities": [{"type": "bot_command", "offset": 0, "length": 6}],
    },
}


def test_line_payload_pass_through_deep_equal() -> None:
    secret = "passthrough-line"
    ch = LineWebhookChannel(channel_secret=secret, channel_access_token="t")
    app = FastAPI()
    ch.mount(app)

    raw = json.dumps(_LINE_SAMPLE, ensure_ascii=False).encode("utf-8")
    sig = compute_line_signature(secret, raw)
    with TestClient(app) as client:
        resp = client.post(
            "/channels/line",
            content=raw,
            headers={"x-line-signature": sig, "content-type": "application/json"},
        )
    assert resp.status_code == 200

    received = ch.receive()
    assert received == _LINE_SAMPLE
    # Defensive: ensure the test's reference value was not mutated.
    assert _LINE_SAMPLE == copy.deepcopy(_LINE_SAMPLE)


def test_telegram_payload_pass_through_deep_equal() -> None:
    ch = TelegramWebhookChannel(secret_token="passthrough-tg", bot_token="9:bot")
    app = FastAPI()
    ch.mount(app)

    with TestClient(app) as client:
        resp = client.post(
            "/channels/telegram",
            json=_TELEGRAM_SAMPLE,
            headers={"x-telegram-bot-api-secret-token": "passthrough-tg"},
        )
    assert resp.status_code == 200

    received = ch.receive()
    assert received == _TELEGRAM_SAMPLE

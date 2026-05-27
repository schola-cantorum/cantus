"""Integration tests for v0.4.5 webhook channel wiring into cantus.serve.serve().

Covers:
- Mount loop only invokes WebhookChannel members (not plain Channels)
- httpx.AsyncClient lifespan creates and closes app.state.http_client
- Coexistence: Skill / dashboard / webhook routes do not collide
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from cantus.core.registry import Registry
from cantus.protocols.skill import register_skill
from cantus.serve import serve
from cantus.serve.channel import LocalMockReceiver
from cantus.serve.channels._signing import compute_line_signature
from cantus.serve.channels.line import LineWebhookChannel


# --- 6.2 mount loop dispatch -----------------------------------------------


class _SpyWebhookChannel:
    """Conforms to WebhookChannel; records whether mount was called."""

    def __init__(self) -> None:
        self.mount_calls: list[Any] = []
        self._queue: list[dict[str, Any]] = []

    def receive(self) -> dict[str, Any]:
        return self._queue.pop(0)

    def send(self, message: dict[str, Any]) -> None:
        return None

    def mount(self, app: Any) -> None:
        self.mount_calls.append(app)


def test_mount_loop_only_calls_webhook_channels() -> None:
    plain = LocalMockReceiver()
    spy = _SpyWebhookChannel()

    app = serve(Registry(), channels=[plain, spy])

    # Plain Channel must not receive mount.
    assert not hasattr(plain, "mount")
    # Spy was mounted exactly once with the FastAPI app instance.
    assert len(spy.mount_calls) == 1
    assert spy.mount_calls[0] is app
    # app.state.channels still carries both channels in the original order.
    assert app.state.channels == [plain, spy]


# --- 6.3 httpx lifespan ----------------------------------------------------


def test_httpx_lifespan_creates_and_closes_client() -> None:
    app = serve(Registry())
    # Before lifespan runs (TestClient context not yet entered), state.http_client
    # may or may not exist depending on FastAPI internals — but inside the
    # context it MUST exist and be open.
    with TestClient(app) as client:
        # Trigger any cold-start; ensure lifespan ran.
        client.get("/openapi.json")
        assert hasattr(app.state, "http_client")
        assert isinstance(app.state.http_client, httpx.AsyncClient)
        assert app.state.http_client.is_closed is False
    # After lifespan exits, the client is closed.
    assert app.state.http_client.is_closed is True


# --- 6.4 coexistence with existing routes ----------------------------------


def _make_registry_with_echo() -> Registry:
    registry = Registry()

    def echo(value: str) -> str:
        """Echo back the input."""
        return value

    registry.register("skill", register_skill(echo))
    return registry


def test_coexistence_with_existing_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A single serve() call accepting LocalMockReceiver + LineWebhookChannel +
    one Skill must expose /skills/echo, /health, AND /channels/line, none
    shadowing each other."""
    monkeypatch.setenv("CANTUS_SERVE_CHANNEL_LINE_SECRET", "co-secret")
    monkeypatch.setenv(
        "CANTUS_SERVE_CHANNEL_LINE_ACCESS_TOKEN", "co-access-token"
    )

    plain = LocalMockReceiver()
    line_ch = LineWebhookChannel()

    registry = _make_registry_with_echo()
    app = serve(registry, channels=[plain, line_ch])

    with TestClient(app) as client:
        # 1. Skill route
        resp = client.post("/skills/echo", json={"value": "hi"})
        assert resp.status_code == 200
        assert resp.json() == {"result": "hi"}

        # 2. Dashboard /health
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json().get("status") == "ok"

        # 3. LINE webhook with correct signature
        raw = json.dumps({"events": [], "destination": "U-x"}).encode("utf-8")
        sig = compute_line_signature("co-secret", raw)
        resp = client.post(
            "/channels/line",
            content=raw,
            headers={"x-line-signature": sig, "content-type": "application/json"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

        # Queue received the event.
        assert line_ch.receive() == {"events": [], "destination": "U-x"}


def test_local_mock_receiver_alone_does_not_mount_channels_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When channels=[LocalMockReceiver()] only, /channels/line MUST be 404
    because no WebhookChannel registered it."""
    app = serve(Registry(), channels=[LocalMockReceiver()])
    with TestClient(app) as client:
        resp = client.post("/channels/line", json={})
        assert resp.status_code == 404

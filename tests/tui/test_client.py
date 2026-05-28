"""Tests for cantus.tui.client.IntrospectionClient.

The client is the read-only data layer of the TUI: it polls the serve
``/introspection`` + ``/health`` endpoints over HTTP, returns parsed data,
maps a workflow 404 to a "no trace" result, and turns connection failures
into an explicit error status instead of letting exceptions escape.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx

BASE = "http://tui-test.local"


def _client(auth_mode: str = "none") -> Any:
    from cantus.tui.client import IntrospectionClient

    return IntrospectionClient(BASE, auth_mode=auth_mode)


@pytest.mark.anyio("asyncio")
async def test_snapshot_returns_parsed_data_via_get() -> None:
    c = _client()
    try:
        with respx.mock(base_url=BASE) as rmock:
            route = rmock.get("/introspection").mock(
                return_value=httpx.Response(
                    200, json={"sessions": [], "queues": []}
                )
            )
            result = await c.snapshot()
            assert result.ok is True
            assert result.data == {"sessions": [], "queues": []}
            assert route.called
            assert route.calls[0].request.method == "GET"
    finally:
        await c.aclose()


@pytest.mark.anyio("asyncio")
async def test_health_returns_parsed_data_via_get() -> None:
    c = _client()
    try:
        with respx.mock(base_url=BASE) as rmock:
            route = rmock.get("/health").mock(
                return_value=httpx.Response(
                    200, json={"status": "ok", "cantus_version": "0.4.8"}
                )
            )
            result = await c.health()
            assert result.ok is True
            assert result.data["cantus_version"] == "0.4.8"
            assert route.calls[0].request.method == "GET"
    finally:
        await c.aclose()


@pytest.mark.anyio("asyncio")
async def test_workflow_200_returns_steps() -> None:
    c = _client()
    try:
        with respx.mock(base_url=BASE) as rmock:
            rmock.get("/introspection/workflows/r1").mock(
                return_value=httpx.Response(
                    200, json={"run_id": "r1", "steps": [{"index": 0}]}
                )
            )
            result = await c.workflow("r1")
            assert result.ok is True
            assert result.data["run_id"] == "r1"
    finally:
        await c.aclose()


@pytest.mark.anyio("asyncio")
async def test_workflow_404_maps_to_none_data() -> None:
    c = _client()
    try:
        with respx.mock(base_url=BASE) as rmock:
            rmock.get("/introspection/workflows/missing").mock(
                return_value=httpx.Response(404, json={"detail": "not found"})
            )
            result = await c.workflow("missing")
            # Reached the server, but the run has no recorded trace.
            assert result.ok is True
            assert result.data is None
    finally:
        await c.aclose()


@pytest.mark.anyio("asyncio")
async def test_connection_error_returns_explicit_error_status() -> None:
    c = _client()
    try:
        with respx.mock(base_url=BASE) as rmock:
            rmock.get("/introspection").mock(
                side_effect=httpx.ConnectError("connection refused")
            )
            result = await c.snapshot()
            assert result.ok is False
            assert result.data is None
            assert result.error  # non-empty, human-readable
    finally:
        await c.aclose()


@pytest.mark.anyio("asyncio")
async def test_bearer_token_sent_from_environment(monkeypatch: Any) -> None:
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "s3cret-token")
    c = _client(auth_mode="bearer")
    try:
        with respx.mock(base_url=BASE) as rmock:
            route = rmock.get("/introspection").mock(
                return_value=httpx.Response(200, json={})
            )
            await c.snapshot()
            sent = route.calls[0].request
            assert sent.headers["authorization"] == "Bearer s3cret-token"
    finally:
        await c.aclose()


@pytest.mark.anyio("asyncio")
async def test_api_key_sent_from_environment(monkeypatch: Any) -> None:
    monkeypatch.setenv("CANTUS_SERVE_API_KEY", "k3y-value")
    c = _client(auth_mode="api-key")
    try:
        with respx.mock(base_url=BASE) as rmock:
            route = rmock.get("/introspection").mock(
                return_value=httpx.Response(200, json={})
            )
            await c.snapshot()
            sent = route.calls[0].request
            assert sent.headers["x-api-key"] == "k3y-value"
    finally:
        await c.aclose()


@pytest.mark.anyio("asyncio")
async def test_repr_and_error_never_leak_token(monkeypatch: Any) -> None:
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "s3cret-token")
    c = _client(auth_mode="bearer")
    try:
        assert "s3cret-token" not in repr(c)
        with respx.mock(base_url=BASE) as rmock:
            rmock.get("/introspection").mock(
                side_effect=httpx.ConnectError("connection refused")
            )
            result = await c.snapshot()
            assert "s3cret-token" not in str(result)
            assert "s3cret-token" not in (result.error or "")
    finally:
        await c.aclose()

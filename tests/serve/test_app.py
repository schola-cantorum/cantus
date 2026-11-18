"""Tests for cantus.serve.app (v0.4.0 cantus-serve-core).

Each test corresponds to one scenario from the
`cantus.serve exposes Tool registry as FastAPI application` Requirement
in the cantus-serve-core capability.
"""

from __future__ import annotations

from typing import Any

import pytest


def _make_registry_with_search_book() -> Any:
    """Build a Registry containing one `search_book` Tool returning a fixed JSON shape."""
    from cantus import Registry, tool

    def search_book(title: str) -> dict[str, Any]:
        """Search books by title."""
        return {"title": title, "found": True}

    instance = tool(search_book)
    return Registry(tools=[instance]), instance


def _make_registry_with_two_tools() -> Any:
    from cantus import Registry, tool

    def search_book(title: str) -> dict[str, Any]:
        """Search books by title."""
        return {"title": title}

    def summarize(text: str, max_words: int = 50) -> str:
        """Summarize text."""
        return f"summary of {len(text)} chars in {max_words} words"

    s1 = tool(search_book)
    s2 = tool(summarize)
    return Registry(tools=[s1, s2]), s1, s2


# --- Construction --------------------------------------------------------


def test_serve_returns_fastapi_instance() -> None:
    from fastapi import FastAPI

    from cantus.core.registry import Registry
    from cantus.serve import serve

    app = serve(Registry())
    assert isinstance(app, FastAPI)


def test_serve_rejects_non_registry_argument() -> None:
    from cantus.serve import serve

    with pytest.raises(TypeError, match="cantus.serve expects a Registry"):
        serve({"not": "a Registry"})  # type: ignore[arg-type]


def test_serve_empty_registry_returns_usable_app() -> None:
    from fastapi.testclient import TestClient

    from cantus.core.registry import Registry
    from cantus.serve import serve

    app = serve(Registry())
    client = TestClient(app)
    # The app must serve OpenAPI even with zero Tools. (Dashboard endpoints
    # like /health are covered by tests/serve/test_dashboard.py.)
    openapi = client.get("/openapi.json").json()
    # No Tool-invoke endpoints exist under /tools/<name> for an empty registry.
    invoke_paths = [p for p in openapi["paths"] if p.startswith("/tools/")]
    assert invoke_paths == []


def test_serve_registry_with_a_tool_has_exactly_one_invoke_path() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    registry, _instance = _make_registry_with_search_book()
    openapi = TestClient(serve(registry)).get("/openapi.json").json()

    invoke_paths = [p for p in openapi["paths"] if p.startswith("/tools/")]
    assert invoke_paths == ["/tools/search_book"]


# --- Tool invoke endpoint ------------------------------------------------


def test_registered_tool_becomes_post_endpoint() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    registry, _instance = _make_registry_with_search_book()
    app = serve(registry)
    client = TestClient(app)

    resp = client.post("/tools/search_book", json={"title": "Brave New World"})
    assert resp.status_code == 200
    body = resp.json()
    assert "result" in body
    assert body["result"] == {"title": "Brave New World", "found": True}


def test_tool_result_matches_direct_run_call() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    registry, instance = _make_registry_with_search_book()
    direct = instance.run(title="Dune")

    app = serve(registry)
    client = TestClient(app)
    resp = client.post("/tools/search_book", json={"title": "Dune"})
    assert resp.status_code == 200
    assert resp.json()["result"] == direct


# --- OpenAPI args_schema byte-equal --------------------------------------


def test_openapi_request_body_schema_matches_spec_for_llm_args_schema() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    registry, s1, s2 = _make_registry_with_two_tools()
    app = serve(registry)
    client = TestClient(app)
    openapi = client.get("/openapi.json").json()

    for the_tool in (s1, s2):
        name = the_tool.spec_for_llm()["name"]
        expected = the_tool.spec_for_llm()["args_schema"]
        path = f"/tools/{name}"
        assert path in openapi["paths"], f"missing path {path!r} in OpenAPI"
        post = openapi["paths"][path]["post"]
        body_schema = post["requestBody"]["content"]["application/json"]["schema"]
        assert body_schema == expected, (
            f"openapi request body schema for /tools/{name} differs from "
            f"spec_for_llm[args_schema] — expected={expected!r} got={body_schema!r}"
        )


# --- Channels stored on app.state ----------------------------------------


def test_channels_kwarg_attaches_to_app_state() -> None:
    from cantus.core.registry import Registry
    from cantus.serve import serve
    from cantus.serve.channel import LocalMockReceiver

    ch = LocalMockReceiver()
    app = serve(Registry(), channels=[ch])
    assert hasattr(app.state, "channels")
    assert isinstance(app.state.channels, list)
    assert len(app.state.channels) == 1
    assert app.state.channels[0] is ch


def test_channels_default_is_empty_list() -> None:
    from cantus.core.registry import Registry
    from cantus.serve import serve

    app = serve(Registry())
    assert hasattr(app.state, "channels")
    assert app.state.channels == []


# --- Row 1: POST /tools/{name} -------------------------------------------

_ADD_SCHEMA = {
    "properties": {
        "a": {"title": "A", "type": "integer"},
        "b": {"title": "B", "type": "integer"},
    },
    "required": ["a", "b"],
    "title": "AddArgs",
    "type": "object",
}


def _add_app(**kwargs: Any) -> Any:
    from cantus import Registry, tool
    from cantus.serve import serve

    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    def ping() -> str:
        """Ping."""
        return "pong"

    def nodoc(x: str) -> str:
        return x

    return serve(Registry(tools=[tool(add), tool(ping), tool(nodoc)]), **kwargs)


def test_post_tools_add_returns_the_sum() -> None:
    from fastapi.testclient import TestClient

    resp = TestClient(_add_app()).post("/tools/add", json={"a": 3, "b": 4})

    assert resp.status_code == 200
    assert resp.json() == {"result": 7}


def test_tools_add_openapi_operation_is_not_deprecated_and_has_the_tool_texts() -> None:
    from fastapi.testclient import TestClient

    operation = TestClient(_add_app()).get("/openapi.json").json()["paths"]["/tools/add"]["post"]

    assert operation["requestBody"]["content"]["application/json"]["schema"] == _ADD_SCHEMA
    assert operation["summary"] == "Invoke Tool: add"
    assert operation["operationId"].startswith("invoke_tool_add")
    assert not operation.get("deprecated")
    assert operation["description"] == "Add two numbers."


def test_tool_without_arguments_answers_200() -> None:
    from fastapi.testclient import TestClient

    resp = TestClient(_add_app()).post("/tools/ping", json={})

    assert resp.status_code == 200
    assert resp.json() == {"result": "pong"}


def test_tool_without_docstring_gets_the_fallback_description() -> None:
    from fastapi.testclient import TestClient

    operation = TestClient(_add_app()).get("/openapi.json").json()["paths"]["/tools/nodoc"]["post"]

    assert operation["description"] == "Invoke cantus Tool 'nodoc'"


# --- Row 3: failures over HTTP -------------------------------------------


def test_tool_that_raises_answers_500() -> None:
    from fastapi.testclient import TestClient

    from cantus import Registry, tool
    from cantus.serve import serve

    def boom(value: str) -> str:
        """Always raises."""
        raise ValueError("kaboom")

    client = TestClient(serve(Registry(tools=[tool(boom)])), raise_server_exceptions=False)

    assert client.post("/tools/boom", json={"value": "x"}).status_code == 500


def test_missing_argument_answers_500() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(_add_app(), raise_server_exceptions=False)

    assert client.post("/tools/add", json={"a": 1}).status_code == 500


def test_non_object_json_body_is_treated_as_an_empty_object() -> None:
    from fastapi.testclient import TestClient

    resp = TestClient(_add_app()).post("/tools/ping", json=[1, 2])

    assert resp.status_code == 200
    assert resp.json() == {"result": "pong"}


def test_malformed_json_body_answers_500() -> None:
    from fastapi.testclient import TestClient

    client = TestClient(_add_app(), raise_server_exceptions=False)
    resp = client.post(
        "/tools/add", content=b"{not json", headers={"content-type": "application/json"}
    )

    assert resp.status_code == 500


# --- Row 4: hooks do not run over HTTP ------------------------------------


def test_pre_and_post_hooks_do_not_run_over_http() -> None:
    from fastapi.testclient import TestClient

    from cantus import Registry, tool
    from cantus.serve import serve

    calls = {"pre": 0, "post": 0}

    def pre(*args: Any, **kwargs: Any) -> None:
        calls["pre"] += 1

    def post(*args: Any, **kwargs: Any) -> None:
        calls["post"] += 1

    def echo(value: str) -> str:
        """Echo back."""
        return value

    registry = Registry(tools=[tool(echo, pre_hook=pre, post_hook=post)])
    resp = TestClient(serve(registry)).post("/tools/echo", json={"value": "own"})

    assert resp.status_code == 200
    assert resp.json() == {"result": "own"}
    assert calls == {"pre": 0, "post": 0}


# --- Row 13: reserved names ----------------------------------------------


@pytest.mark.parametrize(
    ("reserved_name", "kind"),
    [
        ("tools", "dashboard"),
        ("health", "dashboard"),
        ("events", "dashboard"),
        ("channels", "channel"),
        ("introspection", "introspection"),
    ],
)
def test_tool_named_after_a_reserved_path_is_rejected_with_the_full_text(
    reserved_name: str, kind: str
) -> None:
    from cantus import Registry
    from cantus.serve import serve

    class _StubTool:
        name = reserved_name

        def spec_for_llm(self) -> dict[str, Any]:
            return {"name": reserved_name, "description": "", "args_schema": {}}

        def run(self, **kwargs: Any) -> Any:
            return None

    registry = Registry()
    registry.register("tool", _StubTool())
    with pytest.raises(ValueError) as exc:
        serve(registry)

    assert str(exc.value) == (
        f"Tool name '{reserved_name}' collides with a reserved {kind} path "
        f"(reserved {kind} path)"
    )


# --- Row 14: both ways of building a registry ------------------------------


def test_registry_built_from_a_tool_list_serves_every_tool() -> None:
    from fastapi.testclient import TestClient

    from cantus import Registry, tool
    from cantus.serve import serve

    def double(n: int) -> int:
        """Double."""
        return n * 2

    def negate(n: int) -> int:
        """Negate."""
        return -n

    client = TestClient(serve(Registry(tools=[tool(double), tool(negate)])))

    assert client.post("/tools/double", json={"n": 4}).json() == {"result": 8}
    assert client.post("/tools/negate", json={"n": 4}).json() == {"result": -4}


def test_registry_filled_by_register_tool_serves_every_tool() -> None:
    from fastapi.testclient import TestClient

    from cantus import Registry, register_tool
    from cantus.serve import serve

    def double(n: int) -> int:
        """Double."""
        return n * 2

    def negate(n: int) -> int:
        """Negate."""
        return -n

    registry = Registry()
    register_tool(double, registry=registry)
    register_tool(negate, registry=registry)
    client = TestClient(serve(registry))

    assert client.post("/tools/double", json={"n": 4}).json() == {"result": 8}
    assert client.post("/tools/negate", json={"n": 4}).json() == {"result": -4}

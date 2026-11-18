"""Tests for cantus.serve.dashboard (v0.4.0 cantus-serve-core).

Each test corresponds to one scenario from the
`Dashboard endpoints expose registry, health, and event stream` Requirement
in the cantus-serve-core capability.
"""

from __future__ import annotations

from typing import Any

import pytest


def _registry_with_two_tools() -> tuple[Any, Any, Any]:
    from cantus import Registry, tool

    def search_book(title: str) -> dict[str, Any]:
        """Search books by title."""
        return {"title": title}

    def summarize(text: str) -> str:
        """Summarize text."""
        return f"summary of {len(text)} chars"

    s1 = tool(search_book)
    s2 = tool(summarize)
    return Registry(tools=[s1, s2]), s1, s2


# --- GET /tools ---------------------------------------------------------


def test_get_tools_returns_byte_identical_spec_list() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    registry, s1, s2 = _registry_with_two_tools()
    app = serve(registry)
    client = TestClient(app)
    resp = client.get("/tools")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 2
    # registry.names_for("tool") returns sorted names — anchor by name.
    by_name = {b["name"]: b for b in body}
    assert by_name[s1.spec_for_llm()["name"]] == s1.spec_for_llm()
    assert by_name[s2.spec_for_llm()["name"]] == s2.spec_for_llm()


# --- GET /health ---------------------------------------------------------


def test_get_health_returns_status_and_cantus_version() -> None:
    from fastapi.testclient import TestClient

    import cantus
    from cantus.core.registry import Registry
    from cantus.serve import serve

    app = serve(Registry())
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["cantus_version"] == cantus.__version__


# --- GET /events ---------------------------------------------------------


def test_get_events_returns_empty_list_when_no_persistence() -> None:
    from fastapi.testclient import TestClient

    from cantus.core.registry import Registry
    from cantus.serve import serve

    app = serve(Registry())
    client = TestClient(app)
    resp = client.get("/events")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_events_reads_from_app_state_persistence(tmp_path: Any) -> None:
    """Host code may attach a JsonLinesPersistence via app.state.event_persistence."""
    from fastapi.testclient import TestClient

    from cantus.core.event_stream_persistence import JsonLinesPersistence
    from cantus.core.registry import Registry
    from cantus.serve import serve

    log_file = tmp_path / "events.jsonl"
    persistence = JsonLinesPersistence(log_file)
    persistence.append({"e": 1})
    persistence.append({"e": 2})
    persistence.append({"e": 3})

    app = serve(Registry())
    app.state.event_persistence = persistence

    client = TestClient(app)
    resp = client.get("/events")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 3
    assert body[0]["e"] == 1


def test_get_events_respects_limit_query(tmp_path: Any) -> None:
    from fastapi.testclient import TestClient

    from cantus.core.event_stream_persistence import JsonLinesPersistence
    from cantus.core.registry import Registry
    from cantus.serve import serve

    log_file = tmp_path / "events.jsonl"
    persistence = JsonLinesPersistence(log_file)
    for i in range(10):
        persistence.append({"e": i})

    app = serve(Registry())
    app.state.event_persistence = persistence

    client = TestClient(app)
    resp = client.get("/events?limit=3")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 3
    # Most-recent window of 3 from 0..9 → 7, 8, 9 oldest-first.
    assert [item["e"] for item in body] == [7, 8, 9]


# --- dashboard=False -----------------------------------------------------


def test_dashboard_disabled_404s_three_endpoints_but_tool_invoke_works() -> None:
    from fastapi.testclient import TestClient

    from cantus import Registry, tool
    from cantus.config import Settings
    from cantus.serve import serve

    def echo(value: str) -> str:
        """Echo back."""
        return value

    registry = Registry(tools=[tool(echo)])

    app = serve(registry, settings=Settings(dashboard=False))
    client = TestClient(app)

    assert client.get("/tools").status_code == 404
    assert client.get("/health").status_code == 404
    assert client.get("/events").status_code == 404
    # Tool invoke endpoint must still work.
    resp = client.post("/tools/echo", json={"value": "hi"})
    assert resp.status_code == 200
    assert resp.json() == {"result": "hi"}


# --- Reserved dashboard names --------------------------------------------


@pytest.mark.parametrize(
    "reserved_name",
    [
        "tools",
        "health",
        "events",
    ],
)
def test_tool_named_after_reserved_dashboard_path_is_rejected(
    reserved_name: str,
) -> None:
    from cantus.core.registry import Registry
    from cantus.serve import serve

    # Build a stub Tool-like object with a reserved name.
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
        f"Tool name '{reserved_name}' collides with a reserved dashboard path "
        "(reserved dashboard path)"
    )


def test_tool_named_tools_is_rejected_even_with_the_dashboard_off() -> None:
    from cantus import Registry
    from cantus.config import Settings
    from cantus.serve import serve

    class _StubTool:
        name = "tools"

        def spec_for_llm(self) -> dict[str, Any]:
            return {"name": "tools", "description": "", "args_schema": {}}

        def run(self, **kwargs: Any) -> Any:
            return None

    registry = Registry()
    registry.register("tool", _StubTool())
    with pytest.raises(ValueError) as exc:
        serve(registry, settings=Settings(dashboard=False))
    assert str(exc.value) == (
        "Tool name 'tools' collides with a reserved dashboard path "
        "(reserved dashboard path)"
    )


def test_tool_named_channels_rejected_as_reserved_channel_path() -> None:
    """v0.4.5: 'channels' joins the reserved top-level names; collision uses
    a distinct error string so dashboard vs channel collisions stay
    distinguishable in diagnostics."""
    from cantus.core.registry import Registry
    from cantus.serve import serve

    class _StubTool:
        name = "channels"

        def spec_for_llm(self) -> dict[str, Any]:
            return {"name": "channels", "description": "", "args_schema": {}}

        def run(self, **kwargs: Any) -> Any:
            return None

    registry = Registry()
    registry.register("tool", _StubTool())
    with pytest.raises(ValueError) as exc:
        serve(registry)
    assert str(exc.value) == (
        "Tool name 'channels' collides with a reserved channel path "
        "(reserved channel path)"
    )


def test_dashboard_routes_coexist_with_discord_interactions_route() -> None:
    """Task 7.4 — Requirement: /channels/discord/* reserved path namespace.

    Mounting a DiscordRealtimeChannel registers POST /channels/discord/interactions
    beneath the v0.4.5 reserved /channels top-level prefix. The dashboard
    routes (/tools, /health, /events) MUST continue to respond as documented
    — the new sub-path is a sibling, not a shadower.
    """
    from fastapi.testclient import TestClient

    from cantus.core.registry import Registry
    from cantus.serve import DiscordRealtimeChannel, serve

    channel = DiscordRealtimeChannel(
        bot_token="fake-bot-token",
        public_key="aa" * 32,  # 32-byte hex
        application_id="100",
    )
    app = serve(Registry(), channels=[channel])
    client = TestClient(app)

    # Dashboard endpoints respond exactly as v0.4.5 documented.
    assert client.get("/tools").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/events").status_code == 200

    # /channels/discord/interactions is registered (POST-only); GET returns
    # 405 Method Not Allowed, not 404 — proving the route exists but does
    # not shadow dashboard paths.
    discord_get = client.get("/channels/discord/interactions")
    assert discord_get.status_code == 405

    # A request to a non-existent /channels/* sub-path is 404 (sub-path
    # reservation does not implicitly handle siblings).
    assert client.get("/channels/discord/voice").status_code == 404


# --- v0.4.1 cantus-serve-security: dashboard_requires_auth toggle --------


def test_dashboard_requires_auth_default_true_gates_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Under auth_mode=bearer + default dashboard_requires_auth=True, anonymous
    requests to /tools, /health, /events all return 401."""
    import importlib

    from fastapi.testclient import TestClient

    from cantus.serve import serve

    for key in [
        "CANTUS_SERVE_AUTH_MODE",
        "CANTUS_SERVE_BEARER_TOKEN",
        "CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "bearer")
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "correct-secret")
    config_mod = importlib.import_module("cantus.config")
    importlib.reload(config_mod)
    Settings = config_mod.Settings

    registry, _s1, _s2 = _registry_with_two_tools()
    app = serve(registry, settings=Settings())
    client = TestClient(app)

    for path in ("/tools", "/health", "/events"):
        resp = client.get(path)
        assert resp.status_code == 401, (
            f"dashboard endpoint {path} must reject anonymous request "
            f"under default dashboard_requires_auth=True"
        )

    resp = client.get("/health", headers={"Authorization": "Bearer correct-secret"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_dashboard_requires_auth_false_opens_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Under auth_mode=bearer + dashboard_requires_auth=False, the three
    dashboard endpoints accept anonymous requests while /tools/{name} still
    requires auth."""
    import importlib

    from fastapi.testclient import TestClient

    from cantus.serve import serve

    for key in [
        "CANTUS_SERVE_AUTH_MODE",
        "CANTUS_SERVE_BEARER_TOKEN",
        "CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH",
    ]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "bearer")
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "correct-secret")
    monkeypatch.setenv("CANTUS_SERVE_DASHBOARD_REQUIRES_AUTH", "false")
    config_mod = importlib.import_module("cantus.config")
    importlib.reload(config_mod)
    Settings = config_mod.Settings

    registry, s1, _s2 = _registry_with_two_tools()
    app = serve(registry, settings=Settings())
    client = TestClient(app)

    for path in ("/tools", "/health", "/events"):
        resp = client.get(path)
        assert resp.status_code == 200, (
            f"dashboard endpoint {path} must accept anonymous request "
            f"when dashboard_requires_auth=False"
        )

    tool_name = s1.spec_for_llm()["name"]
    resp = client.post(f"/tools/{tool_name}", json={"title": "x"})
    assert resp.status_code == 401


# --- Row 5: GET /tools ----------------------------------------------------


def test_get_tools_lists_literal_specs_sorted_by_name() -> None:
    from fastapi.testclient import TestClient

    from cantus import Registry, tool
    from cantus.serve import serve

    def zeta(text: str) -> str:
        """Shout."""
        return text.upper()

    def alpha(n: int) -> int:
        """Double."""
        return n * 2

    client = TestClient(serve(Registry(tools=[tool(zeta), tool(alpha)])))
    resp = client.get("/tools")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "name": "alpha",
            "description": "Double.",
            "args_schema": {
                "properties": {"n": {"title": "N", "type": "integer"}},
                "required": ["n"],
                "title": "AlphaArgs",
                "type": "object",
            },
        },
        {
            "name": "zeta",
            "description": "Shout.",
            "args_schema": {
                "properties": {"text": {"title": "Text", "type": "string"}},
                "required": ["text"],
                "title": "ZetaArgs",
                "type": "object",
            },
        },
    ]


def test_get_tools_on_an_empty_registry_is_an_empty_list() -> None:
    from fastapi.testclient import TestClient

    from cantus import Registry
    from cantus.serve import serve

    resp = TestClient(serve(Registry())).get("/tools")

    assert resp.status_code == 200
    assert resp.json() == []


def test_get_tools_openapi_summary_and_operation_id() -> None:
    from fastapi.testclient import TestClient

    from cantus import Registry
    from cantus.serve import serve

    operation = TestClient(serve(Registry())).get("/openapi.json").json()["paths"]["/tools"]["get"]

    assert operation["summary"] == "List registered Tools"
    assert operation["operationId"].startswith("dashboard_list_tools")
    assert not operation.get("deprecated")


def test_get_tools_with_the_dashboard_off_is_404_and_invoke_still_works() -> None:
    from fastapi.testclient import TestClient

    from cantus import Registry, tool
    from cantus.config import Settings
    from cantus.serve import serve

    def echo(value: str) -> str:
        """Echo back."""
        return value

    client = TestClient(serve(Registry(tools=[tool(echo)]), settings=Settings(dashboard=False)))

    assert client.get("/tools").status_code == 404
    assert client.post("/tools/echo", json={"value": "hi"}).json() == {"result": "hi"}

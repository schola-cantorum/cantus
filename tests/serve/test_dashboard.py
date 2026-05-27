"""Tests for cantus.serve.dashboard (v0.4.0 cantus-serve-core).

Each test corresponds to one scenario from the
`Dashboard endpoints expose registry, health, and event stream` Requirement
in the cantus-serve-core capability.
"""

from __future__ import annotations

from typing import Any

import pytest


def _registry_with_two_skills() -> tuple[Any, Any, Any]:
    from cantus.core.registry import Registry
    from cantus.protocols.skill import register_skill

    registry = Registry()

    def search_book(title: str) -> dict[str, Any]:
        """Search books by title."""
        return {"title": title}

    def summarize(text: str) -> str:
        """Summarize text."""
        return f"summary of {len(text)} chars"

    s1 = register_skill(search_book)
    s2 = register_skill(summarize)
    registry.register("skill", s1)
    registry.register("skill", s2)
    return registry, s1, s2


# --- GET /skills ---------------------------------------------------------


def test_get_skills_returns_byte_identical_spec_list() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    registry, s1, s2 = _registry_with_two_skills()
    app = serve(registry)
    client = TestClient(app)
    resp = client.get("/skills")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 2
    # registry.names_for("skill") returns sorted names — anchor by name.
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


def test_dashboard_disabled_404s_three_endpoints_but_skill_invoke_works() -> None:
    from fastapi.testclient import TestClient

    from cantus.config import Settings
    from cantus.core.registry import Registry
    from cantus.protocols.skill import register_skill
    from cantus.serve import serve

    def echo(value: str) -> str:
        """Echo back."""
        return value

    instance = register_skill(echo)
    registry = Registry()
    registry.register("skill", instance)

    app = serve(registry, settings=Settings(dashboard=False))
    client = TestClient(app)

    assert client.get("/skills").status_code == 404
    assert client.get("/health").status_code == 404
    assert client.get("/events").status_code == 404
    # Skill invoke endpoint must still work.
    resp = client.post("/skills/echo", json={"value": "hi"})
    assert resp.status_code == 200
    assert resp.json() == {"result": "hi"}


# --- Reserved dashboard names --------------------------------------------


@pytest.mark.parametrize("reserved_name", ["skills", "health", "events"])
def test_skill_named_after_reserved_dashboard_path_is_rejected(
    reserved_name: str,
) -> None:
    from cantus.core.registry import Registry
    from cantus.serve import serve

    # Build a stub Skill-like object with a reserved name.
    class _StubSkill:
        name = reserved_name

        def spec_for_llm(self) -> dict[str, Any]:
            return {"name": reserved_name, "description": "", "args_schema": {}}

        def run(self, **kwargs: Any) -> Any:
            return None

    registry = Registry()
    registry.register("skill", _StubSkill())
    with pytest.raises(ValueError, match="reserved dashboard path"):
        serve(registry)


def test_skill_named_channels_rejected_as_reserved_channel_path() -> None:
    """v0.4.5: 'channels' joins the reserved top-level names; collision uses
    a distinct error string so dashboard vs channel collisions stay
    distinguishable in diagnostics."""
    from cantus.core.registry import Registry
    from cantus.serve import serve

    class _StubSkill:
        name = "channels"

        def spec_for_llm(self) -> dict[str, Any]:
            return {"name": "channels", "description": "", "args_schema": {}}

        def run(self, **kwargs: Any) -> Any:
            return None

    registry = Registry()
    registry.register("skill", _StubSkill())
    with pytest.raises(ValueError, match="reserved channel path"):
        serve(registry)


def test_dashboard_routes_coexist_with_discord_interactions_route() -> None:
    """Task 7.4 — Requirement: /channels/discord/* reserved path namespace.

    Mounting a DiscordRealtimeChannel registers POST /channels/discord/interactions
    beneath the v0.4.5 reserved /channels top-level prefix. The dashboard
    routes (/skills, /health, /events) MUST continue to respond as documented
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
    assert client.get("/skills").status_code == 200
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
    requests to /skills, /health, /events all return 401."""
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

    registry, _s1, _s2 = _registry_with_two_skills()
    app = serve(registry, settings=Settings())
    client = TestClient(app)

    for path in ("/skills", "/health", "/events"):
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
    dashboard endpoints accept anonymous requests while /skills/{name} still
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

    registry, s1, _s2 = _registry_with_two_skills()
    app = serve(registry, settings=Settings())
    client = TestClient(app)

    for path in ("/skills", "/health", "/events"):
        resp = client.get(path)
        assert resp.status_code == 200, (
            f"dashboard endpoint {path} must accept anonymous request "
            f"when dashboard_requires_auth=False"
        )

    skill_name = s1.spec_for_llm()["name"]
    resp = client.post(f"/skills/{skill_name}", json={"title": "x"})
    assert resp.status_code == 401

"""Tests for cantus.serve.app (v0.4.0 cantus-serve-core).

Each test corresponds to one scenario from the
`cantus.serve exposes Skill registry as FastAPI application` Requirement
in the cantus-serve-core capability.
"""

from __future__ import annotations

from typing import Any

import pytest


def _make_registry_with_search_book() -> Any:
    """Build a Registry containing one `search_book` Skill returning a fixed JSON shape."""
    from cantus.core.registry import Registry
    from cantus.protocols.skill import register_skill

    registry = Registry()

    def search_book(title: str) -> dict[str, Any]:
        """Search books by title."""
        return {"title": title, "found": True}

    instance = register_skill(search_book)
    # Decouple test from process-wide singleton — register into a fresh
    # Registry instead of relying on get_registry().
    registry.register("skill", instance)
    return registry, instance


def _make_registry_with_two_skills() -> Any:
    from cantus.core.registry import Registry
    from cantus.protocols.skill import register_skill

    registry = Registry()

    def search_book(title: str) -> dict[str, Any]:
        """Search books by title."""
        return {"title": title}

    def summarize(text: str, max_words: int = 50) -> str:
        """Summarize text."""
        return f"summary of {len(text)} chars in {max_words} words"

    s1 = register_skill(search_book)
    s2 = register_skill(summarize)
    registry.register("skill", s1)
    registry.register("skill", s2)
    return registry, s1, s2


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
    # The app must serve OpenAPI even with zero Skills. (Dashboard endpoints
    # like /health are covered by tests/serve/test_dashboard.py.)
    openapi = client.get("/openapi.json").json()
    # No Skill-invoke endpoints exist under /skills/<name> for empty registry.
    invoke_paths = [
        p for p in openapi["paths"]
        if p.startswith("/skills/") and p != "/skills"
    ]
    assert invoke_paths == []


# --- Skill invoke endpoint -----------------------------------------------


def test_registered_skill_becomes_post_endpoint() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    registry, _instance = _make_registry_with_search_book()
    app = serve(registry)
    client = TestClient(app)

    resp = client.post("/skills/search_book", json={"title": "Brave New World"})
    assert resp.status_code == 200
    body = resp.json()
    assert "result" in body
    assert body["result"] == {"title": "Brave New World", "found": True}


def test_skill_result_matches_direct_run_call() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    registry, instance = _make_registry_with_search_book()
    direct = instance.run(title="Dune")

    app = serve(registry)
    client = TestClient(app)
    resp = client.post("/skills/search_book", json={"title": "Dune"})
    assert resp.status_code == 200
    assert resp.json()["result"] == direct


# --- OpenAPI args_schema byte-equal --------------------------------------


def test_openapi_request_body_schema_matches_spec_for_llm_args_schema() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    registry, s1, s2 = _make_registry_with_two_skills()
    app = serve(registry)
    client = TestClient(app)
    openapi = client.get("/openapi.json").json()

    for skill in (s1, s2):
        name = skill.spec_for_llm()["name"]
        expected = skill.spec_for_llm()["args_schema"]
        path = f"/skills/{name}"
        assert path in openapi["paths"], f"missing path {path!r} in OpenAPI"
        post = openapi["paths"][path]["post"]
        body_schema = post["requestBody"]["content"]["application/json"]["schema"]
        assert body_schema == expected, (
            f"openapi request body schema for /skills/{name} differs from "
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

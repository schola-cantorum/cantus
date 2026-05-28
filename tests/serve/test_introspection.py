"""Tests for cantus.serve.introspection (C2.0 cantus-runtime-introspection-api).

Each test corresponds to one scenario from the
`cantus-runtime-introspection-api` capability: the read-only read-models, the
SessionTracker, the per-concept collectors, and the /introspection endpoint
group registered by register_introspection_routes.
"""

from __future__ import annotations

from typing import Any


# --- Read-models (task 3.1) ----------------------------------------------


def test_skill_entry_serializes_expected_keys() -> None:
    from cantus.serve.introspection import SkillEntry

    entry = SkillEntry(name="search", description="d", args_schema={"type": "object"})
    dumped = entry.model_dump()
    assert set(dumped) == {"name", "description", "args_schema"}
    assert isinstance(dumped["name"], str)
    assert isinstance(dumped["description"], str)
    assert isinstance(dumped["args_schema"], dict)


def test_session_entry_serializes_expected_keys() -> None:
    from cantus.serve.introspection import SessionEntry

    entry = SessionEntry(
        id="r1", source="skill:search", started_at="2026-05-28T00:00:00Z",
        status="completed", event_count=3,
    )
    dumped = entry.model_dump()
    assert set(dumped) == {"id", "source", "started_at", "status", "event_count"}
    assert isinstance(dumped["event_count"], int)


def test_permissions_snapshot_serializes_expected_keys() -> None:
    from cantus.serve.introspection import PermissionsSnapshot

    snap = PermissionsSnapshot(
        auth_mode="bearer", dashboard_requires_auth=True,
        introspection_requires_auth=False, gated_routes=["/skills"],
    )
    dumped = snap.model_dump()
    assert set(dumped) == {
        "auth_mode", "dashboard_requires_auth",
        "introspection_requires_auth", "gated_routes",
    }
    assert isinstance(dumped["dashboard_requires_auth"], bool)
    assert isinstance(dumped["gated_routes"], list)


def test_queue_entry_serializes_with_nullable_depth() -> None:
    from cantus.serve.introspection import QueueEntry

    with_depth = QueueEntry(channel="LocalMockReceiver", kind="other", depth=2)
    without = QueueEntry(channel="X", kind="webhook", depth=None)
    assert set(with_depth.model_dump()) == {"channel", "kind", "depth"}
    assert with_depth.model_dump()["depth"] == 2
    assert without.model_dump()["depth"] is None


def test_workflow_trace_serializes_ordered_steps() -> None:
    from cantus.serve.introspection import WorkflowStep, WorkflowTrace

    trace = WorkflowTrace(
        run_id="r1",
        steps=[WorkflowStep(index=0, kind="action", type="CallSkillAction", summary="x")],
    )
    dumped = trace.model_dump()
    assert set(dumped) == {"run_id", "steps"}
    assert set(dumped["steps"][0]) == {"index", "kind", "type", "summary"}


def test_dataflow_graph_serializes_nodes_and_edges() -> None:
    from cantus.serve.introspection import DataflowEdge, DataflowGraph, DataflowNode

    graph = DataflowGraph(
        nodes=[DataflowNode(id="serve", kind="app", label="serve")],
        edges=[DataflowEdge(source="a", target="b", label="dispatch")],
    )
    dumped = graph.model_dump()
    assert set(dumped) == {"nodes", "edges"}
    assert set(dumped["nodes"][0]) == {"id", "kind", "label"}
    assert set(dumped["edges"][0]) == {"source", "target", "label"}


def test_introspection_snapshot_serializes_rollup_keys() -> None:
    from cantus.serve.introspection import (
        DataflowGraph,
        IntrospectionSnapshot,
        PermissionsSnapshot,
    )

    snap = IntrospectionSnapshot(
        skills=[],
        sessions=[],
        permissions=PermissionsSnapshot(
            auth_mode="none", dashboard_requires_auth=True,
            introspection_requires_auth=True, gated_routes=[],
        ),
        queues=[],
        dataflow=DataflowGraph(nodes=[], edges=[]),
    )
    dumped = snap.model_dump()
    assert set(dumped) == {"skills", "sessions", "permissions", "queues", "dataflow"}


# --- SessionTracker (task 4.1) -------------------------------------------


def test_session_tracker_starts_empty() -> None:
    from cantus.serve.introspection import SessionTracker

    assert SessionTracker().entries() == []


def test_session_tracker_records_one_run_with_all_fields() -> None:
    from cantus.serve.introspection import SessionTracker

    tracker = SessionTracker()
    run_id = tracker.start("skill:search")
    entries = tracker.entries()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.id == run_id
    assert entry.source == "skill:search"
    assert entry.status == "running"
    assert entry.event_count == 0
    assert entry.started_at  # non-empty ISO timestamp


def test_session_tracker_finish_updates_status_and_event_count() -> None:
    from cantus.core.action import FinalAnswerAction
    from cantus.core.event_stream import EventStream
    from cantus.serve.introspection import SessionTracker

    tracker = SessionTracker()
    run_id = tracker.start("skill:x")
    stream = EventStream()
    stream.append(FinalAnswerAction(answer="done"))
    tracker.finish(run_id, status="completed", stream=stream)

    entry = tracker.entries()[0]
    assert entry.status == "completed"
    assert entry.event_count == 1
    assert tracker.event_stream_for(run_id) is stream


def test_session_tracker_bounded_retention_drops_oldest() -> None:
    from cantus.serve.introspection import SessionTracker

    tracker = SessionTracker(max_entries=2)
    first = tracker.start("a")
    tracker.start("b")
    tracker.start("c")

    entries = tracker.entries()
    assert len(entries) == 2
    assert [e.source for e in entries] == ["b", "c"]
    # The evicted run is no longer addressable.
    assert tracker.event_stream_for(first) is None


def test_session_tracker_event_stream_for_unknown_run_is_none() -> None:
    from cantus.serve.introspection import SessionTracker

    assert SessionTracker().event_stream_for("nope") is None


# --- serve() session_tracker wiring (task 4.2) ---------------------------


def _registry_with_echo() -> Any:
    from cantus.core.registry import Registry
    from cantus.protocols.skill import register_skill

    def echo(value: str) -> str:
        """Echo back."""
        return value

    registry = Registry()
    registry.register("skill", register_skill(echo))
    return registry


def test_serve_creates_session_tracker_on_app_state() -> None:
    from cantus.core.registry import Registry
    from cantus.serve import serve
    from cantus.serve.introspection import SessionTracker

    app = serve(Registry())
    assert isinstance(app.state.session_tracker, SessionTracker)


def test_skill_invoke_records_one_session_entry() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    app = serve(_registry_with_echo())
    client = TestClient(app)
    resp = client.post("/skills/echo", json={"value": "hi"})
    assert resp.status_code == 200
    assert resp.json() == {"result": "hi"}

    entries = app.state.session_tracker.entries()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.source == "skill:echo"
    assert entry.status == "completed"
    assert set(entry.model_dump()) == {
        "id", "source", "started_at", "status", "event_count",
    }


# --- collect_skills (task 5.1) -------------------------------------------


def _registry_with_two_named_skills() -> Any:
    from cantus.core.registry import Registry
    from cantus.protocols.skill import register_skill

    def search_web(query: str) -> dict[str, Any]:
        """Search the web."""
        return {"query": query}

    def summarize(text: str) -> str:
        """Summarize."""
        return text[:10]

    registry = Registry()
    registry.register("skill", register_skill(search_web))
    registry.register("skill", register_skill(summarize))
    return registry


def test_collect_skills_projects_specs() -> None:
    from cantus.serve.introspection import collect_skills

    skills = collect_skills(_registry_with_two_named_skills())
    assert len(skills) == 2
    for entry in skills:
        assert set(entry.model_dump()) == {"name", "description", "args_schema"}
    names = {e.name for e in skills}
    assert names == {"search_web", "summarize"}


# --- collect_permissions (task 5.2) --------------------------------------


def _bearer_app(monkeypatch: Any) -> Any:
    import importlib

    from cantus.serve import serve

    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "bearer")
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "s3cret-token")
    config_mod = importlib.import_module("cantus.config")
    importlib.reload(config_mod)
    settings = config_mod.Settings()
    app = serve(_registry_with_echo(), settings=settings)
    return app, settings


def test_collect_permissions_reports_config_without_token(
    monkeypatch: Any,
) -> None:
    from cantus.serve.introspection import collect_permissions

    app, settings = _bearer_app(monkeypatch)
    snapshot = collect_permissions(app, settings)
    dumped = snapshot.model_dump()
    assert dumped["auth_mode"] == "bearer"
    assert isinstance(dumped["dashboard_requires_auth"], bool)
    assert isinstance(dumped["introspection_requires_auth"], bool)
    assert isinstance(dumped["gated_routes"], list)
    # The configured token must never appear in the serialized projection.
    assert "s3cret-token" not in snapshot.model_dump_json()


# --- collect_queues (task 5.3) -------------------------------------------


def test_collect_queues_reports_depth_and_null(monkeypatch: Any) -> None:
    from cantus.serve.channel import LocalMockReceiver
    from cantus.serve.introspection import collect_queues

    class _NoDepthChannel:
        def receive(self) -> dict[str, Any]:
            return {}

        def send(self, message: dict[str, Any]) -> None:
            return None

    receiver = LocalMockReceiver()
    receiver.send({"a": 1})
    receiver.send({"b": 2})

    entries = collect_queues([receiver, _NoDepthChannel()])
    by_channel = {e.channel: e for e in entries}
    assert by_channel["LocalMockReceiver"].depth == 2
    assert by_channel["_NoDepthChannel"].depth is None
    # The channel without the capability is still listed.
    assert len(entries) == 2


# --- collect_dataflow (task 5.4) -----------------------------------------


def test_collect_dataflow_includes_channel_and_skill_nodes() -> None:
    from cantus.serve.channel import LocalMockReceiver
    from cantus.serve.introspection import collect_dataflow

    registry = _registry_with_echo()
    graph = collect_dataflow(registry, [LocalMockReceiver()])
    dumped = graph.model_dump()
    assert len(dumped["nodes"]) > 0
    assert isinstance(dumped["edges"], list)
    labels = {n["label"] for n in dumped["nodes"]}
    assert "echo" in labels  # the registered skill
    assert "LocalMockReceiver" in labels  # the attached channel


# --- workflow projection (task 5.5) --------------------------------------


def test_collect_workflow_projects_ordered_steps() -> None:
    from cantus.core.action import CallSkillAction
    from cantus.core.event_stream import EventStream
    from cantus.core.observation import SkillObservation
    from cantus.serve.introspection import SessionTracker, collect_workflow

    stream = EventStream()
    stream.append(CallSkillAction(skill_name="echo", args={"value": "hi"}))
    stream.append(SkillObservation(skill_name="echo", result="hi"))

    tracker = SessionTracker()
    run_id = tracker.start("skill:echo")
    tracker.finish(run_id, stream=stream)

    trace = collect_workflow(tracker, run_id)
    assert trace is not None
    dumped = trace.model_dump()
    assert dumped["run_id"] == run_id
    assert [s["index"] for s in dumped["steps"]] == [0, 1]
    assert dumped["steps"][0]["kind"] == "action"
    assert dumped["steps"][1]["kind"] == "observation"


def test_collect_workflow_unknown_run_is_none() -> None:
    from cantus.serve.introspection import SessionTracker, collect_workflow

    assert collect_workflow(SessionTracker(), "missing") is None


# --- register_introspection_routes (task 6.1) ----------------------------


def _app_with_routes(channels: Any = None) -> tuple[Any, Any]:
    """Build a bare FastAPI app, populate app.state, register the routes."""
    from fastapi import FastAPI

    from cantus.config import Settings
    from cantus.serve.introspection import (
        SessionTracker,
        register_introspection_routes,
    )

    registry = _registry_with_echo()
    settings = Settings()
    app = FastAPI()
    app.state.settings = settings
    app.state.channels = list(channels or [])
    app.state.session_tracker = SessionTracker()
    register_introspection_routes(app, registry, settings)
    return app, settings


def test_per_concept_endpoints_return_200_and_shape() -> None:
    from fastapi.testclient import TestClient

    app, _ = _app_with_routes()
    client = TestClient(app)

    assert isinstance(client.get("/introspection/skills").json(), list)
    assert isinstance(client.get("/introspection/sessions").json(), list)
    perms = client.get("/introspection/permissions")
    assert perms.status_code == 200
    assert "auth_mode" in perms.json()
    assert isinstance(client.get("/introspection/queues").json(), list)
    dataflow = client.get("/introspection/dataflow")
    assert dataflow.status_code == 200
    assert set(dataflow.json()) == {"nodes", "edges"}


def test_rollup_combines_slices_and_matches_per_concept() -> None:
    from fastapi.testclient import TestClient

    app, _ = _app_with_routes()
    client = TestClient(app)

    rollup = client.get("/introspection")
    assert rollup.status_code == 200
    body = rollup.json()
    assert set(body) == {"skills", "sessions", "permissions", "queues", "dataflow"}
    # The skills slice equals the per-concept skills endpoint body.
    assert body["skills"] == client.get("/introspection/skills").json()


def test_rollup_rejects_post_with_405() -> None:
    from fastapi.testclient import TestClient

    app, _ = _app_with_routes()
    client = TestClient(app)
    assert client.post("/introspection").status_code == 405


def test_workflow_endpoint_returns_trace_and_404() -> None:
    from fastapi.testclient import TestClient

    from cantus.core.action import FinalAnswerAction
    from cantus.core.event_stream import EventStream

    app, _ = _app_with_routes()
    stream = EventStream()
    stream.append(FinalAnswerAction(answer="done"))
    run_id = app.state.session_tracker.start("skill:echo")
    app.state.session_tracker.finish(run_id, stream=stream)

    client = TestClient(app)
    known = client.get(f"/introspection/workflows/{run_id}")
    assert known.status_code == 200
    assert known.json()["run_id"] == run_id
    assert len(known.json()["steps"]) == 1

    assert client.get("/introspection/workflows/does-not-exist").status_code == 404


# --- serve() gating + auth (task 6.2) ------------------------------------


def test_introspection_enabled_returns_200_through_serve() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    app = serve(_registry_with_echo())  # introspection defaults to True
    client = TestClient(app)
    assert client.get("/introspection").status_code == 200
    for slice_path in ("skills", "sessions", "permissions", "queues", "dataflow"):
        assert client.get(f"/introspection/{slice_path}").status_code == 200


def test_introspection_disabled_404s_but_dashboard_and_skill_unaffected() -> None:
    from fastapi.testclient import TestClient

    from cantus.config import Settings
    from cantus.serve import serve

    app = serve(_registry_with_echo(), settings=Settings(introspection=False))
    client = TestClient(app)
    assert client.get("/introspection").status_code == 404
    assert client.get("/introspection/skills").status_code == 404
    # Dashboard + skill-invoke endpoints continue to behave as before.
    assert client.get("/skills").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.post("/skills/echo", json={"value": "hi"}).status_code == 200


def test_introspection_auth_required_rejects_then_accepts(
    monkeypatch: Any,
) -> None:
    import importlib

    from fastapi.testclient import TestClient

    from cantus.serve import serve

    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "bearer")
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "correct-secret")
    monkeypatch.delenv("CANTUS_SERVE_INTROSPECTION_REQUIRES_AUTH", raising=False)
    config_mod = importlib.import_module("cantus.config")
    importlib.reload(config_mod)

    app = serve(_registry_with_echo(), settings=config_mod.Settings())
    client = TestClient(app)
    assert client.get("/introspection").status_code == 401
    ok = client.get("/introspection", headers={"Authorization": "Bearer correct-secret"})
    assert ok.status_code == 200


def test_introspection_requires_auth_false_opens_endpoints(
    monkeypatch: Any,
) -> None:
    import importlib

    from fastapi.testclient import TestClient

    from cantus.serve import serve

    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "bearer")
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "correct-secret")
    monkeypatch.setenv("CANTUS_SERVE_INTROSPECTION_REQUIRES_AUTH", "false")
    config_mod = importlib.import_module("cantus.config")
    importlib.reload(config_mod)

    app = serve(_registry_with_echo(), settings=config_mod.Settings())
    client = TestClient(app)
    assert client.get("/introspection").status_code == 200


# --- reserved path collision (task 6.3) ----------------------------------


def test_skill_named_introspection_rejected() -> None:
    import pytest

    from cantus.core.registry import Registry
    from cantus.serve import serve

    class _StubSkill:
        name = "introspection"

        def spec_for_llm(self) -> dict[str, Any]:
            return {"name": "introspection", "description": "", "args_schema": {}}

        def run(self, **kwargs: Any) -> Any:
            return None

    registry = Registry()
    registry.register("skill", _StubSkill())
    with pytest.raises(ValueError, match="reserved introspection path"):
        serve(registry)

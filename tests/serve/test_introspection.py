"""Tests for cantus.serve.introspection (C2.0 cantus-runtime-introspection-api).

Each test corresponds to one scenario from the
`cantus-runtime-introspection-api` capability: the read-only read-models, the
SessionTracker, the per-concept collectors, and the /introspection endpoint
group registered by register_introspection_routes.
"""

from __future__ import annotations

from typing import Any

import pytest


# --- Read-models (task 3.1) ----------------------------------------------


def test_tool_entry_serializes_expected_keys() -> None:
    from cantus.serve.introspection import ToolEntry

    entry = ToolEntry(name="search", description="d", args_schema={"type": "object"})
    dumped = entry.model_dump()
    assert set(dumped) == {"name", "description", "args_schema"}
    assert isinstance(dumped["name"], str)
    assert isinstance(dumped["description"], str)
    assert isinstance(dumped["args_schema"], dict)


def test_session_entry_serializes_expected_keys() -> None:
    from cantus.serve.introspection import SessionEntry

    entry = SessionEntry(
        id="r1", source="tool:search", started_at="2026-05-28T00:00:00Z",
        status="completed", event_count=3,
    )
    dumped = entry.model_dump()
    assert set(dumped) == {"id", "source", "started_at", "status", "event_count"}
    assert isinstance(dumped["event_count"], int)


def test_permissions_snapshot_serializes_expected_keys() -> None:
    from cantus.serve.introspection import PermissionsSnapshot

    snap = PermissionsSnapshot(
        auth_mode="bearer", dashboard_requires_auth=True,
        introspection_requires_auth=False, gated_routes=["/tools"],
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
        steps=[WorkflowStep(index=0, kind="action", type="CallToolAction", summary="x")],
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
        tools=[],
        sessions=[],
        permissions=PermissionsSnapshot(
            auth_mode="none", dashboard_requires_auth=True,
            introspection_requires_auth=True, gated_routes=[],
        ),
        queues=[],
        dataflow=DataflowGraph(nodes=[], edges=[]),
    )
    dumped = snap.model_dump()
    assert {"tools", "sessions", "permissions", "queues", "dataflow"} <= set(dumped)


# --- SessionTracker (task 4.1) -------------------------------------------


def test_session_tracker_starts_empty() -> None:
    from cantus.serve.introspection import SessionTracker

    assert SessionTracker().entries() == []


def test_session_tracker_records_one_run_with_all_fields() -> None:
    from cantus.serve.introspection import SessionTracker

    tracker = SessionTracker()
    run_id = tracker.start("tool:search")
    entries = tracker.entries()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.id == run_id
    assert entry.source == "tool:search"
    assert entry.status == "running"
    assert entry.event_count == 0
    assert entry.started_at  # non-empty ISO timestamp


def test_session_tracker_finish_updates_status_and_event_count() -> None:
    from cantus.core.action import FinalAnswerAction
    from cantus.core.event_stream import EventStream
    from cantus.serve.introspection import SessionTracker

    tracker = SessionTracker()
    run_id = tracker.start("tool:x")
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
    from cantus import Registry, tool

    def echo(value: str) -> str:
        """Echo back."""
        return value

    return Registry(tools=[tool(echo)])


def test_serve_creates_session_tracker_on_app_state() -> None:
    from cantus.core.registry import Registry
    from cantus.serve import serve
    from cantus.serve.introspection import SessionTracker

    app = serve(Registry())
    assert isinstance(app.state.session_tracker, SessionTracker)


def test_tool_invoke_records_one_session_entry() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    app = serve(_registry_with_echo())
    client = TestClient(app)
    resp = client.post("/tools/echo", json={"value": "hi"})
    assert resp.status_code == 200
    assert resp.json() == {"result": "hi"}

    entries = app.state.session_tracker.entries()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.source == "tool:echo"
    assert entry.status == "completed"
    assert set(entry.model_dump()) == {
        "id", "source", "started_at", "status", "event_count",
    }


# --- tool-invoke EventStream wiring (cantus-serve-tui-mvp task 2.x) ------


def _registry_with_boom() -> Any:
    from cantus import Registry, tool

    def boom(value: str) -> str:
        """Always raises."""
        raise ValueError("kaboom")

    return Registry(tools=[tool(boom)])


def test_tool_invoke_records_two_step_event_stream() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    app = serve(_registry_with_echo())
    client = TestClient(app)
    resp = client.post("/tools/echo", json={"value": "hi"})
    assert resp.status_code == 200

    sessions = client.get("/introspection/sessions").json()
    assert len(sessions) == 1
    run = sessions[0]
    assert run["source"] == "tool:echo"
    assert run["status"] == "completed"
    # The tool invocation records a CallToolAction + ToolObservation.
    assert run["event_count"] == 2

    trace = client.get(f"/introspection/workflows/{run['id']}")
    assert trace.status_code == 200
    steps = trace.json()["steps"]
    assert [s["index"] for s in steps] == [0, 1]
    assert steps[0]["kind"] == "action"
    assert steps[0]["type"] == "CallToolAction"
    assert steps[1]["kind"] == "observation"
    assert steps[1]["type"] == "ToolObservation"


def test_tool_invoke_error_records_tool_error_observation() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    app = serve(_registry_with_boom())
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/tools/boom", json={"value": "x"})
    assert resp.status_code == 500

    sessions = client.get("/introspection/sessions").json()
    assert len(sessions) == 1
    run = sessions[0]
    assert run["status"] == "error"
    assert run["event_count"] == 2

    trace = client.get(f"/introspection/workflows/{run['id']}")
    assert trace.status_code == 200
    steps = trace.json()["steps"]
    assert steps[0]["type"] == "CallToolAction"
    assert steps[1]["kind"] == "observation"
    assert steps[1]["type"] == "ToolErrorObservation"


# --- collect_tools (task 5.1) -------------------------------------------


def _registry_with_two_named_tools() -> Any:
    from cantus import Registry, tool

    def search_web(query: str) -> dict[str, Any]:
        """Search the web."""
        return {"query": query}

    def summarize(text: str) -> str:
        """Summarize."""
        return text[:10]

    return Registry(tools=[tool(search_web), tool(summarize)])


def test_collect_tools_projects_specs() -> None:
    from cantus.serve.introspection import collect_tools

    tools = collect_tools(_registry_with_two_named_tools())
    assert len(tools) == 2
    for entry in tools:
        assert set(entry.model_dump()) == {"name", "description", "args_schema"}
    names = {e.name for e in tools}
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


def test_collect_dataflow_includes_channel_and_tool_nodes() -> None:
    from cantus.serve.channel import LocalMockReceiver
    from cantus.serve.introspection import collect_dataflow

    registry = _registry_with_echo()
    graph = collect_dataflow(registry, [LocalMockReceiver()])
    dumped = graph.model_dump()
    assert len(dumped["nodes"]) > 0
    assert isinstance(dumped["edges"], list)
    labels = {n["label"] for n in dumped["nodes"]}
    assert "echo" in labels  # the registered tool
    assert "LocalMockReceiver" in labels  # the attached channel
    assert {"id": "tool:echo", "kind": "tool", "label": "echo"} in dumped["nodes"]


# --- workflow projection (task 5.5) --------------------------------------


def test_collect_workflow_projects_ordered_steps() -> None:
    from cantus.core.action import CallToolAction
    from cantus.core.event_stream import EventStream
    from cantus.core.observation import ToolObservation
    from cantus.serve.introspection import SessionTracker, collect_workflow

    stream = EventStream()
    stream.append(CallToolAction(tool_name="echo", args={"value": "hi"}))
    stream.append(ToolObservation(tool_name="echo", result="hi"))

    tracker = SessionTracker()
    run_id = tracker.start("tool:echo")
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

    assert isinstance(client.get("/introspection/tools").json(), list)
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
    assert {"tools", "sessions", "permissions", "queues", "dataflow"} <= set(body)
    # The tools slice equals the per-concept tools endpoint body.
    assert body["tools"] == client.get("/introspection/tools").json()


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
    run_id = app.state.session_tracker.start("tool:echo")
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
    for slice_path in ("tools", "sessions", "permissions", "queues", "dataflow"):
        assert client.get(f"/introspection/{slice_path}").status_code == 200


def test_introspection_disabled_404s_but_dashboard_and_tool_unaffected() -> None:
    from fastapi.testclient import TestClient

    from cantus.config import Settings
    from cantus.serve import serve

    app = serve(_registry_with_echo(), settings=Settings(introspection=False))
    client = TestClient(app)
    assert client.get("/introspection").status_code == 404
    assert client.get("/introspection/tools").status_code == 404
    # Dashboard + tool-invoke endpoints continue to behave as before.
    assert client.get("/tools").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.post("/tools/echo", json={"value": "hi"}).status_code == 200


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


def test_tool_named_introspection_rejected() -> None:
    from cantus.core.registry import Registry
    from cantus.serve import serve

    class _StubTool:
        name = "introspection"

        def spec_for_llm(self) -> dict[str, Any]:
            return {"name": "introspection", "description": "", "args_schema": {}}

        def run(self, **kwargs: Any) -> Any:
            return None

    registry = Registry()
    registry.register("tool", _StubTool())
    with pytest.raises(ValueError) as exc:
        serve(registry)
    assert str(exc.value) == (
        "Tool name 'introspection' collides with a reserved introspection path "
        "(reserved introspection path)"
    )


# --- S1: workflow-trace summary de-sensitization (gate-c task 2.1) --------
#
# The workflow endpoint must project a STRUCTURAL summary per step that never
# carries tool argument values, tool result values, or raw exception
# messages. These regression tests pin that contract with the spec's example
# secret strings.


def _registry_with_secret_tool() -> Any:
    from cantus import Registry, tool

    def issue(api_key: str) -> dict[str, Any]:
        """Issue a token for the supplied credential."""
        return {"token": "token-secret-value"}

    return Registry(tools=[tool(issue)])


def _registry_with_secret_boom() -> Any:
    from cantus import Registry, tool

    def leaky(value: str) -> str:
        """Always raises with a message that must not leak."""
        raise ValueError("boom-secret-detail")

    return Registry(tools=[tool(leaky)])


def _run_secret_tool() -> tuple[Any, str]:
    """Invoke the secret tool once with a sensitive arg; return (client, run_id)."""
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    app = serve(_registry_with_secret_tool())
    client = TestClient(app)
    resp = client.post("/tools/issue", json={"api_key": "sk-secret-value"})
    assert resp.status_code == 200
    run_id: str = client.get("/introspection/sessions").json()[0]["id"]
    return client, run_id


def test_workflow_summary_omits_arg_values() -> None:
    client, run_id = _run_secret_tool()
    body = client.get(f"/introspection/workflows/{run_id}").text
    assert "sk-secret-value" not in body


def test_workflow_summary_omits_result_values() -> None:
    client, run_id = _run_secret_tool()
    body = client.get(f"/introspection/workflows/{run_id}").text
    assert "token-secret-value" not in body


def test_workflow_action_summary_has_keys_not_values() -> None:
    client, run_id = _run_secret_tool()
    steps = client.get(f"/introspection/workflows/{run_id}").json()["steps"]
    first = steps[0]
    assert first["type"] == "CallToolAction"
    # The structural summary projects the tool name and the argument key
    # names — but never the argument values.
    assert "issue" in first["summary"]
    assert "api_key" in first["summary"]
    assert "sk-secret-value" not in first["summary"]


def test_workflow_error_summary_omits_message() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    app = serve(_registry_with_secret_boom())
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.post("/tools/leaky", json={"value": "x"})
    assert resp.status_code == 500

    run_id = client.get("/introspection/sessions").json()[0]["id"]
    trace = client.get(f"/introspection/workflows/{run_id}")
    second = trace.json()["steps"][1]
    assert second["type"] == "ToolErrorObservation"
    # The summary carries the (error) type name but not the raw message.
    assert "ToolErrorObservation" in second["summary"]
    assert "boom-secret-detail" not in trace.text


# --- S2: config-cliff startup warning (gate-c task 3.1) -------------------


def _introspection_warnings(caught: Any) -> list[Any]:
    """Warnings about introspection-without-auth captured during a serve build."""
    return [
        w
        for w in caught
        if issubclass(w.category, UserWarning) and "introspection" in str(w.message)
    ]


def test_open_introspection_emits_startup_warning(monkeypatch: Any) -> None:
    import importlib
    import warnings

    from cantus.serve import serve

    config_mod = importlib.import_module("cantus.config")

    # (a) auth_mode=none + introspection=true → a UserWarning naming the
    #     introspection surface; the message must not leak any configured token.
    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "none")
    monkeypatch.setenv("CANTUS_SERVE_BEARER_TOKEN", "tok-should-not-leak")
    monkeypatch.setenv("CANTUS_SERVE_INTROSPECTION", "true")
    importlib.reload(config_mod)
    with pytest.warns(UserWarning, match="introspection") as record:
        serve(_registry_with_echo(), settings=config_mod.Settings())
    text = " ".join(str(w.message) for w in record)
    assert "without authentication" in text
    assert "tok-should-not-leak" not in text

    # (b) auth_mode=bearer + introspection=true → no introspection warning.
    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "bearer")
    importlib.reload(config_mod)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        serve(_registry_with_echo(), settings=config_mod.Settings())
    assert _introspection_warnings(caught) == []

    # (c) auth_mode=none + introspection=false → no introspection warning.
    monkeypatch.setenv("CANTUS_SERVE_AUTH_MODE", "none")
    monkeypatch.setenv("CANTUS_SERVE_INTROSPECTION", "false")
    importlib.reload(config_mod)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        serve(_registry_with_echo(), settings=config_mod.Settings())
    assert _introspection_warnings(caught) == []


# --- S4: workflow endpoint honours the same auth gate (gate-c task 4.1) ---


def test_introspection_workflows_endpoint_gated_by_auth(monkeypatch: Any) -> None:
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

    # No credentials → the workflow path is gated like every other endpoint.
    assert client.get("/introspection/workflows/anything").status_code == 401

    # With the configured token → 200 or 404 (the run does not exist), but the
    # request must never be rejected with 401.
    ok = client.get(
        "/introspection/workflows/anything",
        headers={"Authorization": "Bearer correct-secret"},
    )
    assert ok.status_code in (200, 404)
    assert ok.status_code != 401


# --- Row 7: the rollup's tools list ---------------------------------------


def test_rollup_tools_list_holds_the_literal_entries_for_two_tools() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    body = TestClient(serve(_registry_with_two_named_tools())).get("/introspection").json()

    assert body["tools"] == [
        {
            "name": "search_web",
            "description": "Search the web.",
            "args_schema": {
                "properties": {"query": {"title": "Query", "type": "string"}},
                "required": ["query"],
                "title": "SearchWebArgs",
                "type": "object",
            },
        },
        {
            "name": "summarize",
            "description": "Summarize.",
            "args_schema": {
                "properties": {"text": {"title": "Text", "type": "string"}},
                "required": ["text"],
                "title": "SummarizeArgs",
                "type": "object",
            },
        },
    ]


def test_rollup_tools_list_is_empty_for_an_empty_registry() -> None:
    from fastapi.testclient import TestClient

    from cantus import Registry
    from cantus.serve import serve

    body = TestClient(serve(Registry())).get("/introspection").json()

    assert body["tools"] == []


# --- Row 8: IntrospectionSnapshot.tools -----------------------------------


def _snapshot_parts() -> dict[str, Any]:
    return {
        "sessions": [],
        "permissions": {
            "auth_mode": "none",
            "dashboard_requires_auth": True,
            "introspection_requires_auth": True,
            "gated_routes": [],
        },
        "queues": [],
        "dataflow": {"nodes": [], "edges": []},
    }


def test_snapshot_built_with_tools_dumps_the_literal_list() -> None:
    from cantus.serve.introspection import (
        DataflowGraph,
        IntrospectionSnapshot,
        PermissionsSnapshot,
        ToolEntry,
    )

    entry = ToolEntry(name="add", description="Add.", args_schema={"type": "object"})
    snap = IntrospectionSnapshot(
        tools=[entry],
        sessions=[],
        permissions=PermissionsSnapshot(
            auth_mode="none", dashboard_requires_auth=True,
            introspection_requires_auth=True, gated_routes=[],
        ),
        queues=[],
        dataflow=DataflowGraph(nodes=[], edges=[]),
    )

    assert snap.model_dump()["tools"] == [
        {"name": "add", "description": "Add.", "args_schema": {"type": "object"}}
    ]


def test_snapshot_built_without_any_tool_list_is_rejected() -> None:
    from pydantic import ValidationError

    from cantus.serve.introspection import IntrospectionSnapshot

    with pytest.raises(ValidationError):
        IntrospectionSnapshot.model_validate(_snapshot_parts())


def test_model_validate_leaves_the_input_dict_unchanged() -> None:
    import copy

    from cantus.serve.introspection import IntrospectionSnapshot

    data = {
        "tools": [{"name": "add", "description": "Add.", "args_schema": {}}],
        **_snapshot_parts(),
    }
    before = copy.deepcopy(data)

    IntrospectionSnapshot.model_validate(data)

    assert data == before


def test_openapi_snapshot_schema_requires_tools() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    schema = TestClient(serve(_registry_with_echo())).get("/openapi.json").json()[
        "components"
    ]["schemas"]["IntrospectionSnapshot"]

    assert "tools" in schema["properties"]
    assert "tools" in schema["required"]


# --- Row 10: dataflow nodes and edges for a tool --------------------------


def _add_registry() -> Any:
    from cantus import Registry, tool

    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    return Registry(tools=[tool(add)])


def test_dataflow_has_a_tool_node_and_a_dispatch_edge_without_a_channel() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    body = TestClient(serve(_add_registry())).get("/introspection/dataflow").json()

    assert {"id": "tool:add", "kind": "tool", "label": "add"} in body["nodes"]
    assert {"source": "serve", "target": "tool:add", "label": "dispatch"} in body["edges"]


def test_dataflow_has_a_tool_node_and_a_dispatch_edge_with_a_channel() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve
    from cantus.serve.channel import LocalMockReceiver

    app = serve(_add_registry(), channels=[LocalMockReceiver()])
    body = TestClient(app).get("/introspection/dataflow").json()

    assert {"id": "tool:add", "kind": "tool", "label": "add"} in body["nodes"]
    assert {"source": "serve", "target": "tool:add", "label": "dispatch"} in body["edges"]
    assert {"id": "channel:0", "kind": "channel", "label": "LocalMockReceiver"} in body["nodes"]


# --- Row 11: the session source -------------------------------------------


def test_session_source_is_tool_colon_name_after_a_call() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    client = TestClient(serve(_add_registry()))
    assert client.post("/tools/add", json={"a": 3, "b": 4}).status_code == 200

    assert client.get("/introspection/sessions").json()[-1]["source"] == "tool:add"


def test_session_source_is_tool_colon_name_after_a_failing_call() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    client = TestClient(serve(_registry_with_boom()), raise_server_exceptions=False)
    assert client.post("/tools/boom", json={"value": "x"}).status_code == 500

    assert client.get("/introspection/sessions").json()[-1]["source"] == "tool:boom"


# --- Row 12: trace summaries ----------------------------------------------


def test_trace_summaries_are_structural_literals_without_values() -> None:
    from fastapi.testclient import TestClient

    from cantus import Registry, tool
    from cantus.serve import serve

    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    def boom(value: str) -> str:
        """Always raises."""
        raise ValueError("EXC-MSG-7788")

    app = serve(Registry(tools=[tool(add), tool(boom)]))
    client = TestClient(app, raise_server_exceptions=False)
    assert client.post("/tools/add", json={"a": 11111, "b": 22222}).json() == {"result": 33333}
    assert client.post("/tools/boom", json={"value": "ARG-VALUE-9911"}).status_code == 500

    sessions = client.get("/introspection/sessions").json()
    traces = [client.get(f"/introspection/workflows/{run['id']}").json() for run in sessions]
    steps = [step for trace in traces for step in trace["steps"]]

    assert [(s["type"], s["summary"]) for s in steps] == [
        ("CallToolAction", "CallToolAction tool='add' arg_keys=['a', 'b']"),
        ("ToolObservation", "ToolObservation tool='add' result_type=int"),
        ("CallToolAction", "CallToolAction tool='boom' arg_keys=['value']"),
        ("ToolErrorObservation", "ToolErrorObservation tool='boom'"),
    ]
    text = " ".join(s["summary"] for s in steps)
    for secret in ("11111", "22222", "33333", "ARG-VALUE-9911", "EXC-MSG-7788"):
        assert secret not in text


def test_trace_summary_of_another_event_type_is_its_bare_class_name() -> None:
    from cantus.core.action import FinalAnswerAction
    from cantus.core.event_stream import EventStream
    from cantus.serve.introspection import project_workflow_trace

    stream = EventStream()
    stream.append(FinalAnswerAction(answer="ANSWER-TEXT-5566"))

    trace = project_workflow_trace("r1", stream)

    assert [(s.type, s.summary) for s in trace.steps] == [
        ("FinalAnswerAction", "FinalAnswerAction")
    ]


def test_tools_route_works_on_a_plain_fastapi_app() -> None:
    from fastapi.testclient import TestClient

    app, _ = _app_with_routes()

    response = TestClient(app).get("/introspection/tools")

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "echo",
            "description": "Echo back.",
            "args_schema": {
                "properties": {"value": {"title": "Value", "type": "string"}},
                "required": ["value"],
                "title": "EchoArgs",
                "type": "object",
            },
        }
    ]


# --- Rows 6 and 9: OpenAPI texts of the introspection tool list ------------


def test_openapi_describes_the_tool_list_route_and_the_tool_entry_component() -> None:
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    document = TestClient(serve(_registry_with_echo())).get("/openapi.json").json()
    operation = document["paths"]["/introspection/tools"]["get"]
    component = document["components"]["schemas"]["ToolEntry"]

    assert operation["summary"] == "Registered Tool specs"
    assert operation["operationId"] == "introspection_tools_introspection_tools_get"
    assert not operation.get("deprecated")
    items = operation["responses"]["200"]["content"]["application/json"]["schema"]["items"]
    assert items == {"$ref": "#/components/schemas/ToolEntry"}
    assert sorted(component["properties"]) == ["args_schema", "description", "name"]
    assert sorted(component["required"]) == ["args_schema", "description", "name"]

"""The new-API paths emit no CantusDeprecationWarning (X4 prompt key included)."""

import json
import warnings

import pytest

from cantus import Agent, CantusDeprecationWarning, Registry, register_tool
from cantus.core.observation import ToolErrorObservation
from cantus.grammar.tool_call import build_schema, parse_tool_call
from tests.agent_helpers import ScriptedModel, call_json, final_json, tool_results

_call_json = call_json
_final_json = final_json


def _registry():
    def echo(value: str) -> str:
        """Echo the value."""
        return value

    reg = Registry()
    register_tool(echo, registry=reg)
    return reg


@pytest.fixture
def records():
    """Record every warning raised in the test; the test asserts none is cantus's."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        yield caught


def _assert_no_cantus_warning(caught):
    assert [w for w in caught if issubclass(w.category, CantusDeprecationWarning)] == []


def test_agent_run_with_an_explicit_registry_is_silent_and_prompts_with_tool_key(records):
    reg = _registry()
    model = ScriptedModel([_call_json("echo", value="hi"), _final_json()])
    state = Agent(model, tools=reg).run("q")

    assert tool_results(state.stream) == [("echo", "hi")]
    assert not [e for e in state.stream if isinstance(e, ToolErrorObservation)]
    prompt = json.loads(model.prompts[0])
    assert list(prompt["tools"]) == ["tool"]
    assert [t["name"] for t in prompt["tools"]["tool"]] == ["echo"]
    _assert_no_cantus_warning(records)


def test_grammar_with_an_explicit_registry_is_silent(records):
    reg = _registry()
    schema = build_schema(registry=reg)
    call_branch = schema["properties"]["action"]["oneOf"][0]
    assert call_branch["properties"]["tool_name"]["enum"] == ["echo"]
    parsed = parse_tool_call(_call_json("echo", value="x"), registry=reg)
    assert parsed.tool_name == "echo"
    _assert_no_cantus_warning(records)


def test_serve_routes_are_silent(records):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    app = serve(_registry())
    client = TestClient(app)

    assert client.post("/tools/echo", json={"value": "hi"}).json() == {"result": "hi"}
    assert client.get("/tools").status_code == 200
    for path in (
        "/introspection/tools",
        "/introspection/sessions",
        "/introspection/permissions",
        "/introspection/queues",
        "/introspection/dataflow",
        "/introspection",
    ):
        assert client.get(path).status_code == 200, path
    _assert_no_cantus_warning(records)


def test_workflow_trace_route_after_an_invocation_is_silent(records):
    # T-0009 row 12: the trace route reads the recorded events with the new class names.
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    client = TestClient(serve(_registry()))

    assert client.post("/tools/echo", json={"value": "hi"}).json() == {"result": "hi"}
    run_id = client.get("/introspection/sessions").json()[0]["id"]
    trace = client.get(f"/introspection/workflows/{run_id}")

    assert trace.status_code == 200
    assert [s["type"] for s in trace.json()["steps"]] == ["CallToolAction", "ToolObservation"]
    _assert_no_cantus_warning(records)


def test_the_tool_serve_surface_is_silent_with_bearer_auth_and_logs_nothing(caplog):
    # T-0012 row 16: the Tool names and the primary routes raise no cantus warning and log nothing.
    pytest.importorskip("fastapi")
    import logging

    import cantus
    from fastapi.testclient import TestClient

    from cantus.config import Settings

    caplog.set_level(logging.DEBUG)
    with warnings.catch_warnings():
        warnings.simplefilter("error", cantus.CantusDeprecationWarning)
        import cantus.serve  # noqa: F401
        from cantus.serve import ToolEntry, serve  # noqa: F401
        from cantus.serve.introspection import collect_tools  # noqa: F401

        settings = Settings(auth_mode="bearer", bearer_token="t0k")
        client = TestClient(serve(_registry(), settings=settings))
        headers = {"Authorization": "Bearer t0k"}

        assert client.post("/tools/echo", json={"value": "hi"}, headers=headers).status_code == 200
        assert client.get("/tools", headers=headers).status_code == 200
        assert client.get("/introspection/tools", headers=headers).status_code == 200

    assert [r for r in caplog.records if r.name == "cantus.serve"] == []

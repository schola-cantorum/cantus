"""The new-API paths emit no CantusDeprecationWarning (X4 prompt key included)."""

import json
import warnings

import pytest

from cantus import Agent, CantusDeprecationWarning, Registry, register_tool
from cantus.grammar.tool_call import build_schema, parse_tool_call


class ScriptedModel:
    """Model stub: returns the scripted outputs in order, records prompts."""

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.prompts = []

    def generate(self, prompt, **kwargs):
        self.prompts.append(prompt)
        return self.outputs.pop(0)


def _call_json(name, **args):
    # T-0010 switches this key
    return json.dumps({"thought": "t", "action": {"skill_name": name, "args": args}})


def _final_json():
    return json.dumps({"thought": "d", "action": {"final_answer": "ok"}})


def _registry():
    def echo(value: str) -> str:
        """Echo the value."""
        return value

    reg = Registry()
    register_tool(echo, registry=reg)
    return reg


@pytest.fixture
def no_cantus_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error", CantusDeprecationWarning)
        yield


def test_agent_run_with_an_explicit_registry_is_silent_and_prompts_with_tool_key(
    no_cantus_warning,
):
    reg = _registry()
    model = ScriptedModel([_call_json("echo", value="hi"), _final_json()])
    state = Agent(model, registry=reg).run("q")  # T-0008 switches this to tools=

    assert state.stream  # the loop ran
    prompt = json.loads(model.prompts[0])
    assert list(prompt["tools"]) == ["tool"]
    assert [t["name"] for t in prompt["tools"]["tool"]] == ["echo"]


def test_grammar_with_an_explicit_registry_is_silent(no_cantus_warning):
    reg = _registry()
    schema = build_schema(registry=reg)
    assert schema
    parsed = parse_tool_call(_call_json("echo", value="x"), registry=reg)
    assert parsed.skill_name == "echo"  # T-0009 switches this attribute


def test_serve_routes_are_silent(no_cantus_warning):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from cantus.serve import serve

    app = serve(_registry())
    client = TestClient(app)

    assert client.post("/skills/echo", json={"value": "hi"}).json() == {"result": "hi"}
    assert client.get("/skills").status_code == 200
    for path in (
        "/introspection/skills",
        "/introspection/sessions",
        "/introspection/permissions",
        "/introspection/queues",
        "/introspection/dataflow",
        "/introspection",
    ):
        assert client.get(path).status_code == 200, path

"""The new-API paths emit no CantusDeprecationWarning (X4 prompt key included)."""

import json
import warnings

import pytest

from cantus import Agent, CantusDeprecationWarning, Registry, register_tool
from cantus.core.observation import (
    SkillObservation,  # T-0009 renames this class
    ToolErrorObservation,
)
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
    state = Agent(model, registry=reg).run("q")  # T-0008 switches this to tools=

    observations = [e for e in state.stream if isinstance(e, SkillObservation)]
    assert [(o.skill_name, o.result) for o in observations] == [  # T-0009 switches skill_name
        ("echo", "hi")
    ]
    assert not [e for e in state.stream if isinstance(e, ToolErrorObservation)]
    prompt = json.loads(model.prompts[0])
    assert list(prompt["tools"]) == ["tool"]
    assert [t["name"] for t in prompt["tools"]["tool"]] == ["echo"]
    _assert_no_cantus_warning(records)


def test_grammar_with_an_explicit_registry_is_silent(records):
    reg = _registry()
    schema = build_schema(registry=reg)
    call_branch = schema["properties"]["action"]["oneOf"][0]
    assert call_branch["properties"]["skill_name"]["enum"] == ["echo"]
    parsed = parse_tool_call(_call_json("echo", value="x"), registry=reg)
    assert parsed.skill_name == "echo"  # T-0010 switches this attribute
    _assert_no_cantus_warning(records)


def test_serve_routes_are_silent(records):
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
    _assert_no_cantus_warning(records)

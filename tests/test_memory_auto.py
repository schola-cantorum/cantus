"""AutoMemory — 4-tool LLM-facing wrapper over any lower-tier Memory."""

from __future__ import annotations

import inspect
import re
import textwrap
import warnings

from cantus import Agent, CantusDeprecationWarning
from cantus.core.observation import ToolErrorObservation, ValidationErrorObservation
from cantus.protocols.memory import Memory, ShortTermMemory, Turn
from cantus.protocols.memory_auto import AutoMemory
from cantus.protocols.tool import Tool
from tests.agent_helpers import (
    ScriptedModel,
    call_json,
    final_json,
    prompt_tool_names,
    tool_results,
)


def test_tools_length_and_names():
    auto = AutoMemory(backend=ShortTermMemory(n=5))
    tools = auto.tools
    assert len(tools) == 4
    assert all(isinstance(t, Tool) for t in tools)
    assert [t.name for t in tools] == ["view", "create", "str_replace", "delete"]


def test_auto_not_subclass_of_memory():
    assert not issubclass(AutoMemory, Memory)
    auto = AutoMemory(backend=ShortTermMemory(n=3))
    assert not isinstance(auto, Memory)


def test_each_tool_spec_for_llm_shape():
    auto = AutoMemory(backend=ShortTermMemory(n=5))
    leak_pattern = re.compile(r"_+(?:backend|hook).*")
    for memory_tool in auto.tools:
        spec = memory_tool.spec_for_llm()
        assert set(spec.keys()) == {"name", "description", "args_schema"}
        for key in spec.keys():
            assert not leak_pattern.match(key), f"leaked key: {key}"


def test_create_invokes_backend_remember():
    backend = ShortTermMemory(n=10)
    auto = AutoMemory(backend=backend)
    create_tool = auto.tools[1]  # view, [create], str_replace, delete
    create_tool(user="q", assistant="a")
    recalled = backend.recall("anything")
    assert len(recalled) == 1
    assert recalled[0].user == "q"
    assert recalled[0].assistant == "a"


def test_view_invokes_backend_recall():
    backend = ShortTermMemory(n=10)
    backend.remember(Turn(user="hello", assistant="hi"))
    auto = AutoMemory(backend=backend)
    view_tool = auto.tools[0]
    out = view_tool(query="anything")
    assert isinstance(out, list)
    assert len(out) == 1
    assert out[0]["user"] == "hello"
    assert out[0]["assistant"] == "hi"


def test_tools_property_is_cached():
    auto = AutoMemory(backend=ShortTermMemory(n=5))
    t1 = auto.tools
    t2 = auto.tools
    assert t1 is t2


def test_tools_docstring_contains_warning():
    doc = AutoMemory.tools.fget.__doc__
    assert doc is not None
    assert "LLM has full CRUD access" in doc


def test_auto_memory_tools_drive_backend_through_agent():
    backend = ShortTermMemory(n=10)
    memory = AutoMemory(backend=backend)
    tools_before = memory.tools
    model = ScriptedModel(
        [
            call_json("create", user="q1", assistant="a1"),
            call_json("view", query="q1"),
            call_json("str_replace", query="q1", old="a1", new="b1"),
            call_json("delete", query="q1"),
            final_json(),
        ]
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", CantusDeprecationWarning)
        stream = Agent(model, tools=memory.tools).run("q").stream
    assert tool_results(stream) == [
        ("create", "ok"),
        ("view", [{"user": "q1", "assistant": "a1"}]),
        ("str_replace", 1),
        ("delete", 2),
    ]
    assert not [e for e in stream if isinstance(e, ToolErrorObservation)]
    assert [(t.user, t.assistant) for t in backend.recall("q1")] == [
        ("q1", "a1"),
        ("q1", "b1"),
    ]
    assert prompt_tool_names(model) == ["create", "delete", "str_replace", "view"]
    assert memory.tools is tools_before
    assert len(memory.tools) == 4


def _indented_blocks(doc):
    """Indented code blocks of a docstring, dedented and stripped of outer blank lines."""
    blocks = []
    run = []
    for line in doc.splitlines():
        if line.startswith("    ") or (run and not line.strip()):
            run.append(line)
        else:
            if run:
                blocks.append(run)
            run = []
    if run:
        blocks.append(run)
    return [textwrap.dedent("\n".join(r)).strip("\n") for r in blocks]


class _RecordingMemory(ShortTermMemory):
    def __init__(self, n):
        super().__init__(n=n)
        self.writes = []

    def remember(self, turn):
        self.writes.append((turn.user, turn.assistant))
        super().remember(turn)


def test_tools_docstring_example_runs_and_refuses_password():
    doc = inspect.getdoc(AutoMemory.tools.fget)
    assert "post_hook" not in doc
    blocks = _indented_blocks(doc)
    assert len(blocks) == 1
    backend = _RecordingMemory(n=10)
    model = ScriptedModel(
        [
            call_json("remember", user="my password is hunter2", assistant="ok"),
            call_json("create", user="raw", assistant="write"),
            call_json("remember", user="hi", assistant="yo"),
            final_json(),
        ]
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", CantusDeprecationWarning)
        ns = {"model": model, "backend": backend}
        exec(
            compile(blocks[0], "<AutoMemory.tools docstring>", "exec", dont_inherit=True),
            ns,
        )
        stream = ns["agent"].run("q").stream
    observed = [
        e
        for e in stream
        if isinstance(e, (ToolErrorObservation, ValidationErrorObservation))
    ]
    assert isinstance(observed[0], ToolErrorObservation)
    assert observed[0].tool_name == "remember"
    assert observed[0].message == "ValueError: refusing to store a password"
    assert isinstance(observed[1], ValidationErrorObservation)
    assert tool_results(stream) == [("remember", "ok")]
    assert backend.writes == [("hi", "yo")]
    assert [(t.user, t.assistant) for t in backend.recall("hi")] == [("hi", "yo")]

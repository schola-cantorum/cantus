"""AutoMemory — 4-tool LLM-facing wrapper over any lower-tier Memory."""

from __future__ import annotations

import re

from cantus.protocols.memory import Memory, ShortTermMemory, Turn
from cantus.protocols.memory_auto import AutoMemory
from cantus.protocols.skill import Skill


def test_tools_length_and_names():
    auto = AutoMemory(backend=ShortTermMemory(n=5))
    tools = auto.tools
    assert len(tools) == 4
    assert all(isinstance(t, Skill) for t in tools)
    assert [t.name for t in tools] == ["view", "create", "str_replace", "delete"]


def test_auto_not_subclass_of_memory():
    assert not issubclass(AutoMemory, Memory)
    auto = AutoMemory(backend=ShortTermMemory(n=3))
    assert not isinstance(auto, Memory)


def test_each_tool_spec_for_llm_shape():
    auto = AutoMemory(backend=ShortTermMemory(n=5))
    leak_pattern = re.compile(r"_+(?:backend|hook).*")
    for tool in auto.tools:
        spec = tool.spec_for_llm()
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

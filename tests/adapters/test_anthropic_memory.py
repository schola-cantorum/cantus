"""expose_as_anthropic_memory_tool — pure dict adapter for Anthropic Memory spec."""

from __future__ import annotations

import json

import pytest

from cantus.adapters import expose_as_anthropic_memory_tool
from cantus.protocols.memory import AutoMemory, ShortTermMemory


def test_dict_shape():
    mem = ShortTermMemory(n=3)
    tool_dict = expose_as_anthropic_memory_tool(mem)
    assert set(tool_dict.keys()) == {"type", "name", "description", "commands"}
    assert tool_dict["type"] == "memory"
    assert tool_dict["name"] == "memory"
    assert isinstance(tool_dict["description"], str) and tool_dict["description"]


def test_four_command_keys():
    mem = ShortTermMemory(n=3)
    tool_dict = expose_as_anthropic_memory_tool(mem)
    commands = tool_dict["commands"]
    assert set(commands.keys()) == {"view", "create", "str_replace", "delete"}
    for name, cmd in commands.items():
        assert set(cmd.keys()) == {"description", "args_schema"}, f"shape mismatch in {name}"
        assert isinstance(cmd["description"], str)
        assert isinstance(cmd["args_schema"], dict)


def test_json_dumps_succeeds():
    auto = AutoMemory(backend=ShortTermMemory(n=5))
    tool_dict = expose_as_anthropic_memory_tool(auto)
    serialised = json.dumps(tool_dict)
    assert isinstance(serialised, str) and len(serialised) > 0
    # Round-trip — content survives JSON serialisation
    assert json.loads(serialised) == tool_dict


@pytest.mark.parametrize(
    "bad",
    [
        "not a memory",
        {"backend": "fake"},
        None,
        42,
        [ShortTermMemory(n=1)],  # list of Memory, not a Memory itself
    ],
)
def test_rejects_non_memory_input(bad):
    with pytest.raises(TypeError, match="expects Memory or AutoMemory"):
        expose_as_anthropic_memory_tool(bad)

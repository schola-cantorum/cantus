"""expose_as_anthropic_memory_tool — cantus Memory → Anthropic Memory tool dict.

Returns a pure Python `dict` (no callables, no Memory instance references)
matching the Anthropic Memory tool spec: a 4-action surface (`view`,
`create`, `str_replace`, `delete`) over a Skill-shaped command schema. The
returned dict round-trips through `json.dumps` so host code can feed it
straight into `client.messages.create(tools=[...])`.

The adapter does NOT wire the LLM's tool_use callbacks back into the
Memory backend — that's host code's responsibility. The returned dict is
opaque to the Memory instance; the host pattern is:

    1. send `tool_dict` to Anthropic via `tools=[...]`
    2. when Claude emits `tool_use` with `name="memory"`, dispatch the
       `command` argument back into the appropriate `memory.recall` /
       `memory.remember` call

Foot-gun warning carry-over (v0.3.1 audit Trap-10): under this tool_use
loop, the LLM has full CRUD access to the memory backend with no built-in
filter. For production, wrap individual commands with validation in the
host dispatch layer.
"""

from __future__ import annotations

from typing import Any

from cantus.protocols.memory import AutoMemory, Memory

_VIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Substring to match against stored turn content (case-insensitive).",
        }
    },
    "required": ["query"],
}

_CREATE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "user": {"type": "string", "description": "User-side content of the turn."},
        "assistant": {"type": "string", "description": "Assistant-side content of the turn."},
    },
    "required": ["user", "assistant"],
}

_STR_REPLACE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Substring filter selecting turns to modify."},
        "old": {"type": "string", "description": "Old substring to replace within matched turns."},
        "new": {"type": "string", "description": "Replacement substring."},
    },
    "required": ["query", "old", "new"],
}

_DELETE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Substring filter selecting turns to delete."},
    },
    "required": ["query"],
}


def expose_as_anthropic_memory_tool(memory: Memory | AutoMemory) -> dict[str, Any]:
    """Return a JSON-serialisable Anthropic Memory tool dict for the given Memory."""
    if not isinstance(memory, (Memory, AutoMemory)):
        raise TypeError(
            f"expose_as_anthropic_memory_tool expects Memory or AutoMemory, "
            f"got {type(memory).__name__}"
        )

    backend_name = type(memory).__name__
    description = f"Cantus {backend_name} exposed as Anthropic Memory tool"

    commands: dict[str, dict[str, Any]] = {
        "view": {
            "description": "Recall stored turns whose user or assistant field matches the query.",
            "args_schema": _VIEW_SCHEMA,
        },
        "create": {
            "description": "Remember a new (user, assistant) turn.",
            "args_schema": _CREATE_SCHEMA,
        },
        "str_replace": {
            "description": "Find matching turns and replace `old` with `new` in their fields.",
            "args_schema": _STR_REPLACE_SCHEMA,
        },
        "delete": {
            "description": "Mark stored turns matching the query as deleted (backend-dependent).",
            "args_schema": _DELETE_SCHEMA,
        },
    }

    return {
        "type": "memory",
        "name": "memory",
        "description": description,
        "commands": commands,
    }


__all__ = ["expose_as_anthropic_memory_tool"]

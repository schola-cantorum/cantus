"""Tool-call grammar — `thought` free, `args` strict.

The grammar describes model output as JSON of shape:

    {"thought": <free string>,
     "action": {"tool_name": <one-of-registered>, "args": <tool-arguments>}}

or, for termination:

    {"thought": <free string>,
     "action": {"final_answer": <free string>}}

We deliberately do NOT constrain `thought`. CRANE/GAD show that
collapsing the reasoning channel into a strict schema costs accuracy on
small models. Only the action target and its args are checked.

`build_schema` returns a JSON schema for use with `outlines` /
`xgrammar`; cantus's own `Agent` does not constrain decoding with it.
`parse_tool_call` checks a raw model output and the registered tool catalog; it is
more lenient than the schema (`args` may be omitted, and the old action key is accepted). Both take the `Registry` to use as
`registry=`; leaving it out falls back to the process-wide registry and is deprecated.
A model output that still names the tool with the old action key is accepted for one
deprecation window.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from cantus._deprecation import warn_legacy
from cantus.core._legacy_events import accepts_legacy_keyword
from cantus.core.registry import Registry, _get_global_registry


def _action_name(action: dict[str, Any]) -> tuple[bool, Any]:
    """Read the tool name from an action dict that has no ``final_answer``.

    The one place that decides which key names the tool. ``tool_name`` wins whenever
    the key is present, whatever its value; only without it does the legacy key count.

    Args:
        action: The action object of a model output.

    Returns:
        ``(True, value)`` with the raw value of the name key, or ``(False, None)``
        when neither key is present.
    """
    if "tool_name" in action:
        return True, action["tool_name"]
    if "skill_name" in action:  # legacy-alias
        warn_legacy("W13")
        return True, action["skill_name"]  # legacy-alias
    return False, None


@accepts_legacy_keyword
@dataclass
class ParsedToolCall:
    """What `parse_tool_call` returns: a tool call, or a final answer.

    For a final answer ``tool_name`` is ``None`` and ``args`` is empty.
    """

    thought: str
    tool_name: str | None
    args: dict[str, Any]
    final_answer: str | None


def _resolve_registry(registry: Registry | None, variant: str) -> Registry:
    """Return the registry to use; fall back to the global one with W12 when it holds tools."""
    if registry is not None:
        return registry
    fallback = _get_global_registry()
    if fallback.names_for("tool"):
        warn_legacy("W12", variant=variant)
    return fallback


class GrammarError(ValueError):
    """Raised when a tool-call payload does not match the grammar."""


def build_schema(registry: Registry | None = None) -> dict[str, Any]:
    """Return the JSON schema for the tool-call grammar.

    `tool_name` is a string enum drawn from the tools registered in
    ``registry`` at the time of the call; call it again after the tools change.
    With no registered tool it is a plain string.

    Args:
        registry: The registry whose tool names fill the enum. Leaving it out is
            deprecated: the process-wide registry is used, and a warning is emitted
            when that registry holds tools.

    Returns:
        The JSON schema as a dict.
    """
    reg = _resolve_registry(registry, "build_schema")
    tool_names = reg.names_for("tool")
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "ToolCall",
        "type": "object",
        "required": ["thought", "action"],
        "properties": {
            "thought": {"type": "string"},
            "action": {
                "type": "object",
                "oneOf": [
                    {
                        "required": ["tool_name", "args"],
                        "properties": {
                            "tool_name": (
                                {"type": "string", "enum": tool_names}
                                if tool_names
                                else {"type": "string"}
                            ),
                            "args": {"type": "object"},
                        },
                        "additionalProperties": False,
                    },
                    {
                        "required": ["final_answer"],
                        "properties": {
                            "final_answer": {"type": "string", "minLength": 1},
                        },
                        "additionalProperties": False,
                    },
                ],
            },
        },
        "additionalProperties": False,
    }


def parse_tool_call(raw: str, registry: Registry | None = None) -> ParsedToolCall:
    """Parse and validate a raw model output.

    Args:
        raw: The model output, expected to be a JSON object.
        registry: The registry whose tool names are accepted. An empty registry accepts
            any name. Leaving it out is deprecated: the process-wide registry is used,
            and a warning is emitted when that registry holds tools.

    Returns:
        The parsed call: ``tool_name`` and ``args`` for a tool call, ``final_answer``
        for a termination.

    Raises:
        GrammarError: If the output does not match the grammar.
    """
    reg = _resolve_registry(registry, "parse_tool_call")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GrammarError(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GrammarError("top-level must be an object")
    if "thought" not in data or "action" not in data:
        raise GrammarError("missing required keys 'thought' or 'action'")
    thought = data["thought"]
    if not isinstance(thought, str):
        raise GrammarError("thought must be a string")
    action = data["action"]
    if not isinstance(action, dict):
        raise GrammarError("action must be an object")

    if "final_answer" in action:
        if not isinstance(action["final_answer"], str):
            raise GrammarError("final_answer must be a string")
        if len(action["final_answer"]) < 1:
            raise GrammarError(
                "final_answer must be a non-empty string (minLength: 1)"
            )
        return ParsedToolCall(
            thought=thought,
            tool_name=None,
            args={},
            final_answer=action["final_answer"],
        )

    _, tool_name = _action_name(action)
    if not isinstance(tool_name, str):
        raise GrammarError("tool_name must be a string")
    if reg.names_for("tool") and tool_name not in reg.names_for("tool"):
        raise GrammarError(
            f"tool_name '{tool_name}' not registered; "
            f"available: {reg.names_for('tool')}"
        )
    args = action.get("args", {})
    if not isinstance(args, dict):
        raise GrammarError("args must be an object")
    return ParsedToolCall(
        thought=thought,
        tool_name=tool_name,
        args=args,
        final_answer=None,
    )

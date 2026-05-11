"""Tool-call grammar — `thought` free, `args` strict.

The LLM is constrained to emit JSON of shape:

    {"thought": <free string>,
     "action": {"skill_name": <one-of-registered>, "args": <skill-pydantic>}}

or, for termination:

    {"thought": <free string>,
     "action": {"final_answer": <free string>}}

We deliberately do NOT constrain `thought`. CRANE/GAD show that
collapsing the reasoning channel into a strict schema costs accuracy on
small models. Only the action target and its args are checked.

`build_grammar` returns a JSON schema for use with `outlines` /
`xgrammar`. `parse_tool_call` validates a raw model output against the
schema and the registered skill catalog.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from cantus.core.registry import Registry, get_registry


@dataclass
class ParsedToolCall:
    thought: str
    skill_name: str | None
    args: dict[str, Any]
    final_answer: str | None


class GrammarError(ValueError):
    """Raised when a tool-call payload does not match the grammar."""


def build_schema(registry: Registry | None = None) -> dict[str, Any]:
    """Return the JSON schema for the tool-call grammar.

    `skill_name` is a string enum drawn from currently-registered
    skills; the agent calls this each turn so newly-registered skills
    appear immediately.
    """
    reg = registry or get_registry()
    skill_names = reg.names_for("skill")
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
                        "required": ["skill_name", "args"],
                        "properties": {
                            "skill_name": (
                                {"type": "string", "enum": skill_names}
                                if skill_names
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
    """Parse + validate a raw model output. Raises GrammarError on mismatch."""
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
    reg = registry or get_registry()

    if "final_answer" in action:
        if not isinstance(action["final_answer"], str):
            raise GrammarError("final_answer must be a string")
        if len(action["final_answer"]) < 1:
            raise GrammarError(
                "final_answer must be a non-empty string (minLength: 1)"
            )
        return ParsedToolCall(
            thought=thought,
            skill_name=None,
            args={},
            final_answer=action["final_answer"],
        )

    skill_name = action.get("skill_name")
    if not isinstance(skill_name, str):
        raise GrammarError("skill_name must be a string")
    if reg.names_for("skill") and skill_name not in reg.names_for("skill"):
        raise GrammarError(
            f"skill_name '{skill_name}' not registered; "
            f"available: {reg.names_for('skill')}"
        )
    args = action.get("args", {})
    if not isinstance(args, dict):
        raise GrammarError("args must be an object")
    return ParsedToolCall(
        thought=thought,
        skill_name=skill_name,
        args=args,
        final_answer=None,
    )

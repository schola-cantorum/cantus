"""Pure-function translators between cantus Tier 2 dataclasses and provider wire formats.

Adapters call these functions instead of inheriting from a shared base
class — that keeps provider-specific quirks (OpenAI's JSON-string tool
arguments, Anthropic's content-block messages and top-level system kwarg)
out of any abstraction layer and into one obvious place.

Every translator function is deterministic and side-effect free; tests
can call them with hand-crafted dicts without any SDK installed.
"""

from __future__ import annotations

import json
from typing import Any

from cantus.model.chat import ChatResponse, Message, ToolCall


# ---------------------------------------------------------------------------
# OpenAI Chat Completions
# ---------------------------------------------------------------------------

_OPENAI_FINISH_TO_STOP: dict[str, str] = {
    "stop": "end_turn",
    "length": "max_tokens",
    "tool_calls": "tool_use",
}


def to_openai_messages(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert Tier 2 Messages to the OpenAI Chat Completions wire format."""
    out: list[dict[str, Any]] = []
    for msg in messages:
        if msg.role == "tool":
            out.append(
                {
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id,
                }
            )
            continue

        entry: dict[str, Any] = {"role": msg.role, "content": msg.content}
        if msg.tool_calls:
            entry["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments),
                    },
                }
                for tc in msg.tool_calls
            ]
        out.append(entry)
    return out


def from_openai_response(raw: Any) -> ChatResponse:
    """Convert an OpenAI ChatCompletion response (dict or pydantic object) to ChatResponse."""
    data = _as_dict(raw)
    choice = data["choices"][0]
    msg_data = choice["message"]

    tool_calls = extract_tool_calls_openai(msg_data)
    message = Message(
        role="assistant",
        content=msg_data.get("content") or "",
        tool_calls=tool_calls,
    )

    finish = choice.get("finish_reason", "stop")
    stop_reason = _OPENAI_FINISH_TO_STOP.get(finish, "error")

    usage_raw = data.get("usage")
    usage: dict[str, int] | None
    if usage_raw is not None:
        usage = {
            "input_tokens": int(usage_raw.get("prompt_tokens", 0)),
            "output_tokens": int(usage_raw.get("completion_tokens", 0)),
        }
    else:
        usage = None

    return ChatResponse(message=message, stop_reason=stop_reason, usage=usage, raw=raw)


def extract_tool_calls_openai(message_dict: dict[str, Any]) -> list[ToolCall]:
    """Pull `tool_calls` out of an OpenAI message dict, parsing JSON arguments."""
    raw_calls = message_dict.get("tool_calls") or []
    return [
        ToolCall(
            id=tc["id"],
            name=tc["function"]["name"],
            arguments=json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {},
        )
        for tc in raw_calls
    ]


# ---------------------------------------------------------------------------
# Anthropic Messages
# ---------------------------------------------------------------------------

_ANTHROPIC_STOP_REASONS: set[str] = {
    "end_turn",
    "max_tokens",
    "stop_sequence",
    "tool_use",
}


def to_anthropic_messages(
    messages: list[Message],
) -> tuple[str | None, list[dict[str, Any]]]:
    """Convert Tier 2 Messages to Anthropic format.

    Returns ``(system, messages)`` because Anthropic puts the system prompt
    in a top-level kwarg, not in the ``messages`` list. The first system
    message wins; subsequent system messages are concatenated with newlines.
    """
    system_parts: list[str] = []
    out: list[dict[str, Any]] = []
    for msg in messages:
        if msg.role == "system":
            system_parts.append(msg.content)
            continue

        if msg.role == "tool":
            out.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content,
                        }
                    ],
                }
            )
            continue

        if msg.tool_calls:
            blocks: list[dict[str, Any]] = []
            if msg.content:
                blocks.append({"type": "text", "text": msg.content})
            for tc in msg.tool_calls:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    }
                )
            out.append({"role": msg.role, "content": blocks})
        else:
            out.append({"role": msg.role, "content": msg.content})

    system = "\n".join(system_parts) if system_parts else None
    return system, out


def from_anthropic_response(raw: Any) -> ChatResponse:
    """Convert an Anthropic Messages response to ChatResponse."""
    data = _as_dict(raw)
    blocks = data.get("content") or []

    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in blocks:
        btype = block.get("type")
        if btype == "text":
            text_parts.append(block.get("text", ""))
        elif btype == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=block["id"],
                    name=block["name"],
                    arguments=block.get("input") or {},
                )
            )

    stop_raw = data.get("stop_reason", "end_turn")
    stop_reason = stop_raw if stop_raw in _ANTHROPIC_STOP_REASONS else "error"

    usage_raw = data.get("usage")
    usage: dict[str, int] | None
    if usage_raw is not None:
        usage = {
            "input_tokens": int(usage_raw.get("input_tokens", 0)),
            "output_tokens": int(usage_raw.get("output_tokens", 0)),
        }
    else:
        usage = None

    message = Message(
        role="assistant",
        content="".join(text_parts),
        tool_calls=tool_calls,
    )
    return ChatResponse(message=message, stop_reason=stop_reason, usage=usage, raw=raw)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _as_dict(obj: Any) -> dict[str, Any]:
    """Normalise SDK pydantic models or raw dicts to a plain dict for translation."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    raise TypeError(f"cannot normalise object of type {type(obj).__name__} to dict")

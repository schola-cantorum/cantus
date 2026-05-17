"""Tier 2 ChatModel Protocol — the multi-provider chat-style interface.

This is **Tier 2** of the cantus dual-tier API (see ARCH-1 in
`openspec/discussions/cantus-framework-shift.md`). Tier 1 is the existing
`cantus.core.agent.ModelHandle` Protocol — a minimal `generate(prompt) -> str`
interface used by `Agent`. Tier 2 introduces chat-style messages with tool use
and streaming, modeled after the OpenAI Chat Completions shape because every
cross-provider adapter we ship (OpenAI, Anthropic, and future Google / Groq /
NVIDIA) either natively uses or trivially translates to that shape.

Tier 2 models do NOT replace Tier 1. To plug a `ChatModel` into an `Agent`,
wrap it with `cantus.model.bridge.ChatModelAsHandle` — this preserves the
Tier 1 mental model (prompt-in / string-out) on the Agent side while
exposing the rich chat interface to advanced callers.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable


@dataclass
class ToolCall:
    """A single tool invocation requested by the model.

    `arguments` is the already-parsed JSON object, NOT the raw JSON string —
    every adapter normalises before populating this field so downstream code
    never sees provider-specific encodings.
    """

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Message:
    """One turn in a chat conversation, OpenAI-shaped.

    For `role="tool"`, both `tool_call_id` and `name` MUST be set so the
    provider can match the response back to the originating tool call.
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class ChatResponse:
    """A single assistant turn produced by `ChatModel.chat(...)`.

    `raw` is an intentional escape hatch — callers needing provider-native
    features (Anthropic content blocks, OpenAI logprobs, etc.) can reach
    into it without us having to model every provider's full surface.
    """

    message: Message
    stop_reason: Literal["end_turn", "tool_use", "max_tokens", "stop_sequence", "error"]
    usage: dict[str, int] | None = None
    raw: Any = None


@runtime_checkable
class ChatModel(Protocol):
    """The Tier 2 multi-provider chat interface.

    Implementations live under `cantus.model.providers.*` (one module per
    provider). The Protocol is `runtime_checkable` so tests and bridges
    can verify shape without importing concrete adapters.

    `stream` yields text deltas only — tool-call streaming is intentionally
    deferred (see design.md, decision "v0.2.0 stream() 只 yield 文字 delta")
    because provider event shapes diverge sharply.
    """

    supports_tool_use: bool
    model_id: str

    def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> ChatResponse: ...

    def stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> Iterator[str]: ...

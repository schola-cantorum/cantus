"""Contract tests for ChatModelAsHandle — Tier 2 → Tier 1 bridge."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from cantus.model.bridge import ChatModelAsHandle
from cantus.model.chat import ChatResponse, Message


@dataclass
class _RecordingChat:
    """Captures calls so tests can assert what messages reached the model."""

    response_text: str = "echo"
    received_messages: list[list[Message]] = field(default_factory=list)
    received_kwargs: list[dict[str, Any]] = field(default_factory=list)
    supports_tool_use: bool = True
    model_id: str = "fake/test"

    def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        self.received_messages.append(list(messages))
        self.received_kwargs.append(dict(kwargs))
        return ChatResponse(
            message=Message(role="assistant", content=self.response_text),
            stop_reason="end_turn",
        )

    def stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        yield self.response_text


def test_bridge_exposes_tier_1_generate_method_shape():
    """Bridge must duck-type to cantus.core.agent.ModelHandle (`.generate(prompt) -> str`)."""
    bridge = ChatModelAsHandle(_RecordingChat())
    assert hasattr(bridge, "generate")
    assert callable(bridge.generate)
    # Smoke: invoking with a single positional prompt returns a string
    result = bridge.generate("hi")
    assert isinstance(result, str)


def test_generate_without_system_sends_only_user_message():
    chat = _RecordingChat(response_text="reply")
    bridge = ChatModelAsHandle(chat)
    out = bridge.generate("hello")
    assert out == "reply"
    assert len(chat.received_messages) == 1
    sent = chat.received_messages[0]
    assert len(sent) == 1
    assert sent[0].role == "user"
    assert sent[0].content == "hello"


def test_generate_with_system_prepends_system_message():
    chat = _RecordingChat(response_text="terse-reply")
    bridge = ChatModelAsHandle(chat, system="be terse")
    out = bridge.generate("hello")
    assert out == "terse-reply"
    sent = chat.received_messages[0]
    assert len(sent) == 2
    assert sent[0].role == "system"
    assert sent[0].content == "be terse"
    assert sent[1].role == "user"
    assert sent[1].content == "hello"


def test_generate_passes_kwargs_through_to_chat():
    chat = _RecordingChat()
    bridge = ChatModelAsHandle(chat)
    bridge.generate("hi", max_tokens=42, temperature=0.7)
    assert chat.received_kwargs[0] == {"max_tokens": 42, "temperature": 0.7}


def test_empty_system_string_is_treated_as_no_system():
    chat = _RecordingChat()
    bridge = ChatModelAsHandle(chat, system="")
    bridge.generate("hi")
    sent = chat.received_messages[0]
    assert len(sent) == 1
    assert sent[0].role == "user"


def test_returned_value_is_message_content_string():
    chat = _RecordingChat(response_text="exact")
    bridge = ChatModelAsHandle(chat)
    result = bridge.generate("anything")
    assert isinstance(result, str)
    assert result == "exact"

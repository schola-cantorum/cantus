"""Contract tests for cantus.model.chat — Tier 2 ChatModel Protocol + dataclasses."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from cantus.model.chat import (
    ChatModel,
    ChatResponse,
    Message,
    ToolCall,
)


def test_message_role_literals_accept_four_canonical_roles():
    for role in ("system", "user", "assistant", "tool"):
        Message(role=role, content="x")


def test_message_default_content_is_empty_string_and_tool_calls_is_empty_list():
    msg = Message(role="user")
    assert msg.content == ""
    assert msg.tool_calls == []
    assert msg.tool_call_id is None
    assert msg.name is None


def test_tool_role_message_carries_tool_call_id_and_name():
    msg = Message(
        role="tool",
        content='{"result": 4}',
        tool_call_id="call_abc",
        name="add",
    )
    assert msg.tool_call_id == "call_abc"
    assert msg.name == "add"


def test_tool_call_arguments_is_parsed_dict_not_raw_string():
    tc = ToolCall(id="call_1", name="search", arguments={"q": "cantus"})
    assert tc.arguments == {"q": "cantus"}
    assert isinstance(tc.arguments, dict)


def test_chat_response_exposes_message_stop_reason_usage_and_raw_escape_hatch():
    msg = Message(role="assistant", content="hi")
    resp = ChatResponse(
        message=msg,
        stop_reason="end_turn",
        usage={"input_tokens": 5, "output_tokens": 1},
        raw={"any": "provider-native object"},
    )
    assert resp.message is msg
    assert resp.stop_reason == "end_turn"
    assert resp.usage == {"input_tokens": 5, "output_tokens": 1}
    assert resp.raw == {"any": "provider-native object"}


def test_chat_response_defaults_usage_and_raw_to_none():
    resp = ChatResponse(
        message=Message(role="assistant", content="ok"),
        stop_reason="end_turn",
    )
    assert resp.usage is None
    assert resp.raw is None


class _FakeChat:
    supports_tool_use = True
    model_id = "fake/test"

    def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        return ChatResponse(
            message=Message(role="assistant", content="echo"),
            stop_reason="end_turn",
        )

    def stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        yield "echo"


def test_custom_implementation_satisfies_chat_model_protocol_via_runtime_check():
    instance = _FakeChat()
    assert isinstance(instance, ChatModel)


def test_chat_model_protocol_rejects_object_missing_required_attribute():
    class Incomplete:
        model_id = "x"

        def chat(self, messages, tools=None, **kwargs):
            return ChatResponse(message=Message(role="assistant"), stop_reason="end_turn")

        def stream(self, messages, tools=None, **kwargs):
            yield ""

    # Missing supports_tool_use → not a ChatModel
    assert not isinstance(Incomplete(), ChatModel)


def test_stream_yields_str_deltas_only_no_tool_call_objects():
    instance = _FakeChat()
    deltas = list(instance.stream([Message(role="user", content="hi")]))
    assert all(isinstance(d, str) for d in deltas)


@pytest.mark.parametrize(
    "role,tool_call_id_required,name_required",
    [
        ("system", False, False),
        ("user", False, False),
        ("assistant", False, False),
        ("tool", True, True),
    ],
)
def test_message_role_field_requirement_table(
    role: str, tool_call_id_required: bool, name_required: bool
) -> None:
    """Mirrors the spec's role-requirements example table (model-providers/spec.md)."""
    msg = Message(
        role=role,
        content="x",
        tool_call_id="cid" if tool_call_id_required else None,
        name="n" if name_required else None,
    )
    assert (msg.tool_call_id is not None) == tool_call_id_required
    assert (msg.name is not None) == name_required

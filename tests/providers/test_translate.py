"""Contract tests for cantus.model.providers._translate translator functions."""

from __future__ import annotations

import pytest

from cantus.model.chat import Message, ToolCall
from cantus.model.providers._translate import (
    extract_tool_calls_openai,
    from_anthropic_response,
    from_openai_response,
    to_anthropic_messages,
    to_openai_messages,
)


# ---------- to_openai_messages ----------------------------------------------


def test_to_openai_messages_preserves_role_and_content_for_basic_turns():
    msgs = [
        Message(role="system", content="be terse"),
        Message(role="user", content="hi"),
        Message(role="assistant", content="hello"),
    ]
    out = to_openai_messages(msgs)
    assert out == [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_to_openai_messages_emits_tool_calls_with_json_string_arguments():
    msg = Message(
        role="assistant",
        content="",
        tool_calls=[ToolCall(id="call_1", name="search", arguments={"q": "cantus"})],
    )
    out = to_openai_messages([msg])
    assert out[0]["role"] == "assistant"
    assert out[0]["tool_calls"] == [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "search", "arguments": '{"q": "cantus"}'},
        }
    ]


def test_to_openai_messages_tool_role_includes_tool_call_id():
    msg = Message(
        role="tool",
        content='{"result": 4}',
        tool_call_id="call_1",
        name="add",
    )
    out = to_openai_messages([msg])
    assert out == [
        {
            "role": "tool",
            "content": '{"result": 4}',
            "tool_call_id": "call_1",
        }
    ]


# ---------- to_anthropic_messages -------------------------------------------


def test_to_anthropic_messages_extracts_system_as_top_level_string():
    msgs = [
        Message(role="system", content="be terse"),
        Message(role="user", content="hi"),
    ]
    system, out = to_anthropic_messages(msgs)
    assert system == "be terse"
    assert out == [{"role": "user", "content": "hi"}]


def test_to_anthropic_messages_returns_none_system_when_no_system_message():
    msgs = [Message(role="user", content="hi")]
    system, out = to_anthropic_messages(msgs)
    assert system is None
    assert out == [{"role": "user", "content": "hi"}]


def test_to_anthropic_messages_assistant_with_tool_calls_uses_content_blocks():
    msg = Message(
        role="assistant",
        content="thinking aloud",
        tool_calls=[ToolCall(id="tu_1", name="search", arguments={"q": "x"})],
    )
    _, out = to_anthropic_messages([msg])
    assert out == [
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "thinking aloud"},
                {"type": "tool_use", "id": "tu_1", "name": "search", "input": {"q": "x"}},
            ],
        }
    ]


def test_to_anthropic_messages_tool_role_becomes_user_tool_result_block():
    msg = Message(
        role="tool",
        content="42",
        tool_call_id="tu_1",
        name="add",
    )
    _, out = to_anthropic_messages([msg])
    assert out == [
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "tu_1", "content": "42"},
            ],
        }
    ]


def test_to_anthropic_messages_skips_assistant_text_block_when_content_empty():
    msg = Message(
        role="assistant",
        content="",
        tool_calls=[ToolCall(id="tu_1", name="x", arguments={})],
    )
    _, out = to_anthropic_messages([msg])
    # No empty text block; only the tool_use
    assert out[0]["content"] == [
        {"type": "tool_use", "id": "tu_1", "name": "x", "input": {}},
    ]


# ---------- from_openai_response --------------------------------------------


def test_from_openai_response_extracts_text_and_maps_stop_reason():
    raw = {
        "choices": [
            {
                "message": {"role": "assistant", "content": "hi there"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }
    resp = from_openai_response(raw)
    assert resp.message.role == "assistant"
    assert resp.message.content == "hi there"
    assert resp.stop_reason == "end_turn"
    assert resp.usage == {"input_tokens": 5, "output_tokens": 2}
    assert resp.raw is raw


def test_from_openai_response_parses_tool_calls_arguments_as_dict():
    raw = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "search", "arguments": '{"q": "cantus"}'},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }
    resp = from_openai_response(raw)
    assert resp.stop_reason == "tool_use"
    assert resp.message.tool_calls == [
        ToolCall(id="call_1", name="search", arguments={"q": "cantus"})
    ]


@pytest.mark.parametrize(
    "openai_finish,expected",
    [
        ("stop", "end_turn"),
        ("length", "max_tokens"),
        ("tool_calls", "tool_use"),
        ("content_filter", "error"),
    ],
)
def test_from_openai_response_finish_reason_mapping(openai_finish, expected):
    raw = {
        "choices": [
            {
                "message": {"role": "assistant", "content": "x"},
                "finish_reason": openai_finish,
            }
        ],
    }
    assert from_openai_response(raw).stop_reason == expected


# ---------- from_anthropic_response -----------------------------------------


def test_from_anthropic_response_concatenates_text_blocks():
    raw = {
        "content": [
            {"type": "text", "text": "Hello "},
            {"type": "text", "text": "world"},
        ],
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 5, "output_tokens": 2},
    }
    resp = from_anthropic_response(raw)
    assert resp.message.content == "Hello world"
    assert resp.stop_reason == "end_turn"
    assert resp.usage == {"input_tokens": 5, "output_tokens": 2}
    assert resp.raw is raw


def test_from_anthropic_response_extracts_tool_use_blocks():
    raw = {
        "content": [
            {"type": "text", "text": "checking"},
            {"type": "tool_use", "id": "tu_1", "name": "search", "input": {"q": "x"}},
        ],
        "stop_reason": "tool_use",
    }
    resp = from_anthropic_response(raw)
    assert resp.message.content == "checking"
    assert resp.message.tool_calls == [
        ToolCall(id="tu_1", name="search", arguments={"q": "x"})
    ]
    assert resp.stop_reason == "tool_use"


def test_from_anthropic_response_handles_empty_content_list():
    raw = {"content": [], "stop_reason": "end_turn"}
    resp = from_anthropic_response(raw)
    assert resp.message.content == ""
    assert resp.message.tool_calls == []


# ---------- extract_tool_calls_openai (round-trip helper) -------------------


def test_extract_tool_calls_openai_returns_empty_list_when_field_absent():
    assert extract_tool_calls_openai({"role": "assistant", "content": "hi"}) == []


def test_extract_tool_calls_openai_round_trips_via_to_openai_messages():
    original = [ToolCall(id="c1", name="add", arguments={"a": 1, "b": 2})]
    msg = Message(role="assistant", content="", tool_calls=original)
    dumped = to_openai_messages([msg])[0]
    recovered = extract_tool_calls_openai(dumped)
    assert recovered == original

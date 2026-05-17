"""Contract tests for AnthropicChatModel — auth, system extraction, request shape, response translation.

Uses SDK-level mocks (monkeypatch on `anthropic.Anthropic`) instead of VCR
cassettes; see test_openai_adapter.py for the same rationale.
"""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from cantus.model.chat import Message
from cantus.model.providers._common import MissingAPIKeyError
from cantus.model.providers.anthropic import AnthropicChatModel


class _DictResponse:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def model_dump(self) -> dict[str, Any]:
        return self._data


class _FakeMessages:
    def __init__(self, response_dict: dict[str, Any]) -> None:
        self._response_dict = response_dict
        self.last_kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        return _DictResponse(self._response_dict)


class _FakeClient:
    def __init__(self, response_dict: dict[str, Any], **init_kwargs: Any) -> None:
        self.init_kwargs = init_kwargs
        self.messages = _FakeMessages(response_dict)


@pytest.fixture
def install_fake_anthropic(monkeypatch):
    captured: dict[str, Any] = {}

    def _factory(response_dict: dict[str, Any]):
        def _fake_constructor(**init_kwargs: Any):
            client = _FakeClient(response_dict, **init_kwargs)
            captured["client"] = client
            return client

        import anthropic

        monkeypatch.setattr(anthropic, "Anthropic", _fake_constructor)
        return captured

    return _factory


# ---------- auth ------------------------------------------------------------


def test_constructor_resolves_api_key_from_env_var(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")
    model = AnthropicChatModel(model_id="claude-sonnet-4-6")
    assert model._api_key == "sk-from-env"


def test_constructor_explicit_api_key_wins_over_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")
    model = AnthropicChatModel(model_id="claude-sonnet-4-6", api_key="sk-explicit")
    assert model._api_key == "sk-explicit"


def test_missing_api_key_raises_missing_api_key_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError) as exc:
        AnthropicChatModel(model_id="claude-sonnet-4-6")
    assert "ANTHROPIC_API_KEY" in str(exc.value)


# ---------- system extraction (top-level kwarg, NOT in messages) -----------


def test_system_message_becomes_top_level_kwarg(install_fake_anthropic):
    captured = install_fake_anthropic(
        {
            "content": [{"type": "text", "text": "ok"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 4, "output_tokens": 1},
        }
    )
    model = AnthropicChatModel(model_id="claude-sonnet-4-6", api_key="sk-x")
    model.chat(
        [
            Message(role="system", content="be terse"),
            Message(role="user", content="hi"),
        ]
    )
    last = captured["client"].messages.last_kwargs
    assert last["system"] == "be terse"
    assert last["messages"] == [{"role": "user", "content": "hi"}]


def test_no_system_message_means_no_system_kwarg(install_fake_anthropic):
    captured = install_fake_anthropic(
        {
            "content": [{"type": "text", "text": "ok"}],
            "stop_reason": "end_turn",
        }
    )
    model = AnthropicChatModel(model_id="claude-sonnet-4-6", api_key="sk-x")
    model.chat([Message(role="user", content="hi")])
    last = captured["client"].messages.last_kwargs
    assert "system" not in last


# ---------- chat request shape + response translation -----------------------


def test_chat_sends_model_and_translated_messages(install_fake_anthropic):
    captured = install_fake_anthropic(
        {
            "content": [{"type": "text", "text": "hello there"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 3, "output_tokens": 2},
        }
    )
    model = AnthropicChatModel(model_id="claude-sonnet-4-6", api_key="sk-x")
    resp = model.chat(
        [Message(role="user", content="hi")],
        max_tokens=1024,
    )
    last = captured["client"].messages.last_kwargs
    assert last["model"] == "claude-sonnet-4-6"
    assert last["max_tokens"] == 1024
    assert resp.message.content == "hello there"
    assert resp.stop_reason == "end_turn"
    assert resp.usage == {"input_tokens": 3, "output_tokens": 2}


def test_chat_passes_tools_when_provided(install_fake_anthropic):
    captured = install_fake_anthropic(
        {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}
    )
    model = AnthropicChatModel(model_id="m", api_key="sk-x")
    tools = [{"name": "search", "description": "x", "input_schema": {"type": "object"}}]
    model.chat([Message(role="user", content="hi")], tools=tools)
    assert captured["client"].messages.last_kwargs["tools"] == tools


def test_chat_omits_tools_key_when_none(install_fake_anthropic):
    captured = install_fake_anthropic(
        {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}
    )
    model = AnthropicChatModel(model_id="m", api_key="sk-x")
    model.chat([Message(role="user", content="hi")])
    assert "tools" not in captured["client"].messages.last_kwargs


# ---------- protocol attributes ---------------------------------------------


def test_supports_tool_use_is_true():
    mp = pytest.MonkeyPatch()
    mp.setenv("ANTHROPIC_API_KEY", "x")
    try:
        assert AnthropicChatModel(model_id="m").supports_tool_use is True
    finally:
        mp.undo()


def test_model_id_attribute_is_set():
    mp = pytest.MonkeyPatch()
    mp.setenv("ANTHROPIC_API_KEY", "x")
    try:
        assert AnthropicChatModel(model_id="claude-sonnet-4-6").model_id == "claude-sonnet-4-6"
    finally:
        mp.undo()


# ---------- stream ----------------------------------------------------------


def test_stream_yields_only_text_deltas(monkeypatch):
    class _StreamCtx:
        def __init__(self):
            self.text_stream = iter(["Hello ", "world"])

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class _StreamMessages:
        def stream(self, **kwargs):
            return _StreamCtx()

    class _StreamClient:
        messages = _StreamMessages()

    import anthropic

    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: _StreamClient())

    model = AnthropicChatModel(model_id="m", api_key="sk-x")
    deltas = list(model.stream([Message(role="user", content="hi")], max_tokens=64))
    assert deltas == ["Hello ", "world"]

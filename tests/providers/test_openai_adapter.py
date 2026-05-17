"""Contract tests for OpenAIChatModel — auth, base_url, request shape, response translation.

Uses SDK-level mocks (monkeypatch on `openai.OpenAI`) instead of VCR cassettes
because v0.2.0 ships without recorded API keys; the translator round-trip is
already exercised by `tests/providers/test_translate.py`. Cassettes will land
when v0.2.1 adds live integration smoke against real provider endpoints.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from cantus.model.chat import Message
from cantus.model.providers._common import MissingAPIKeyError
from cantus.model.providers.openai import OpenAIChatModel


class _FakeChoices:
    def __init__(self, response_dict: dict[str, Any]) -> None:
        self._response_dict = response_dict

    def create(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        return _DictResponse(self._response_dict)


class _DictResponse:
    """Stands in for openai.types.ChatCompletion — translator uses model_dump()."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def model_dump(self) -> dict[str, Any]:
        return self._data


class _FakeClient:
    def __init__(self, response_dict: dict[str, Any], **init_kwargs: Any) -> None:
        self.init_kwargs = init_kwargs
        self.chat = SimpleNamespace(completions=_FakeChoices(response_dict))


@pytest.fixture
def install_fake_openai(monkeypatch):
    """Replace `openai.OpenAI` with a fake whose response is test-controlled."""

    captured: dict[str, Any] = {}

    def _factory(response_dict: dict[str, Any]):
        def _fake_constructor(**init_kwargs: Any):
            client = _FakeClient(response_dict, **init_kwargs)
            captured["client"] = client
            return client

        import openai

        monkeypatch.setattr(openai, "OpenAI", _fake_constructor)
        return captured

    return _factory


# ---------- auth ------------------------------------------------------------


def test_constructor_resolves_api_key_from_env_var(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    monkeypatch.delenv("OPENAI_PROJECT", raising=False)
    model = OpenAIChatModel(model_id="gpt-4o-mini")
    # private accessor by design — we expose via _get_client below
    assert model._api_key == "sk-from-env"


def test_constructor_explicit_api_key_wins_over_env(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    model = OpenAIChatModel(model_id="gpt-4o-mini", api_key="sk-explicit")
    assert model._api_key == "sk-explicit"


def test_missing_api_key_raises_missing_api_key_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError) as exc:
        OpenAIChatModel(model_id="gpt-4o-mini")
    assert "OPENAI_API_KEY" in str(exc.value)


# ---------- base_url --------------------------------------------------------


def test_base_url_passes_through_to_sdk_client(install_fake_openai):
    captured = install_fake_openai(
        {
            "choices": [
                {"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
            ]
        }
    )
    model = OpenAIChatModel(
        model_id="m",
        api_key="sk-x",
        base_url="https://integrate.api.nvidia.com/v1",
    )
    model.chat([Message(role="user", content="hi")])
    assert captured["client"].init_kwargs["base_url"] == "https://integrate.api.nvidia.com/v1"


def test_base_url_not_passed_when_none(install_fake_openai):
    captured = install_fake_openai(
        {
            "choices": [
                {"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
            ]
        }
    )
    model = OpenAIChatModel(model_id="m", api_key="sk-x")
    model.chat([Message(role="user", content="hi")])
    assert "base_url" not in captured["client"].init_kwargs


# ---------- chat request shape + response translation -----------------------


def test_chat_sends_model_and_translated_messages(install_fake_openai):
    captured = install_fake_openai(
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "hello there"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
        }
    )
    model = OpenAIChatModel(model_id="gpt-4o-mini", api_key="sk-x")
    resp = model.chat(
        [
            Message(role="system", content="be terse"),
            Message(role="user", content="hi"),
        ]
    )
    last = captured["client"].chat.completions.last_kwargs
    assert last["model"] == "gpt-4o-mini"
    assert last["messages"] == [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "hi"},
    ]
    assert resp.message.role == "assistant"
    assert resp.message.content == "hello there"
    assert resp.stop_reason == "end_turn"
    assert resp.usage == {"input_tokens": 3, "output_tokens": 2}


def test_chat_passes_tools_when_provided(install_fake_openai):
    captured = install_fake_openai(
        {
            "choices": [
                {"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
            ]
        }
    )
    model = OpenAIChatModel(model_id="m", api_key="sk-x")
    tools = [{"type": "function", "function": {"name": "search", "parameters": {}}}]
    model.chat([Message(role="user", content="hi")], tools=tools)
    assert captured["client"].chat.completions.last_kwargs["tools"] == tools


def test_chat_omits_tools_key_when_none(install_fake_openai):
    captured = install_fake_openai(
        {
            "choices": [
                {"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
            ]
        }
    )
    model = OpenAIChatModel(model_id="m", api_key="sk-x")
    model.chat([Message(role="user", content="hi")])
    assert "tools" not in captured["client"].chat.completions.last_kwargs


def test_chat_forwards_extra_kwargs_like_temperature(install_fake_openai):
    captured = install_fake_openai(
        {
            "choices": [
                {"message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
            ]
        }
    )
    model = OpenAIChatModel(model_id="m", api_key="sk-x")
    model.chat([Message(role="user", content="hi")], temperature=0.2, max_tokens=64)
    last = captured["client"].chat.completions.last_kwargs
    assert last["temperature"] == 0.2
    assert last["max_tokens"] == 64


# ---------- protocol attributes ---------------------------------------------


def test_supports_tool_use_is_true():
    monkeypatch_env = pytest.MonkeyPatch()
    monkeypatch_env.setenv("OPENAI_API_KEY", "x")
    try:
        assert OpenAIChatModel(model_id="m").supports_tool_use is True
    finally:
        monkeypatch_env.undo()


def test_model_id_attribute_is_set():
    monkeypatch_env = pytest.MonkeyPatch()
    monkeypatch_env.setenv("OPENAI_API_KEY", "x")
    try:
        assert OpenAIChatModel(model_id="my-model").model_id == "my-model"
    finally:
        monkeypatch_env.undo()


# ---------- stream ----------------------------------------------------------


def test_stream_yields_only_text_deltas(monkeypatch):
    """stream() must yield str text-deltas only (no tool-call delta in v0.2.0)."""

    class _DeltaChunk:
        def __init__(self, content):
            self.choices = [SimpleNamespace(delta=SimpleNamespace(content=content))]

    def _fake_create(**kwargs):
        # Mix in a None-content chunk (e.g. role-only opener) to ensure it's filtered
        yield _DeltaChunk(None)
        yield _DeltaChunk("Hello ")
        yield _DeltaChunk("world")

    class _StreamClient:
        chat = SimpleNamespace(completions=SimpleNamespace(create=_fake_create))

    import openai

    monkeypatch.setattr(openai, "OpenAI", lambda **kw: _StreamClient())

    model = OpenAIChatModel(model_id="m", api_key="sk-x")
    deltas = list(model.stream([Message(role="user", content="hi")]))
    assert deltas == ["Hello ", "world"]

"""Contract tests for GroqChatModel — auth, request shape, translator reuse.

Uses SDK-level mocks (monkeypatch on `groq.Groq`) matching the v0.2.0
OpenAI/Anthropic test convention. Groq's wire is OpenAI-compatible, so this
adapter directly reuses the existing `to_openai_messages` / `from_openai_response`
pure functions from `_translate.py` — there is NO `to_groq_messages`.
"""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from cantus.model.chat import Message
from cantus.model.providers._common import MissingAPIKeyError


# ---------- fake groq SDK ---------------------------------------------------


class _FakeChoices:
    def __init__(self, response_dict: dict[str, Any]) -> None:
        self._response_dict = response_dict
        self.last_kwargs: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        return _DictResponse(self._response_dict)


class _DictResponse:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def model_dump(self) -> dict[str, Any]:
        return self._data


class _FakeClient:
    def __init__(self, response_dict: dict[str, Any], **init_kwargs: Any) -> None:
        self.init_kwargs = init_kwargs
        self.chat = SimpleNamespace(completions=_FakeChoices(response_dict))


@pytest.fixture
def install_fake_groq(monkeypatch):
    """Inject a fake `groq` module into sys.modules (groq SDK isn't installed in CI)."""

    captured: dict[str, Any] = {}

    def _factory(response_dict: dict[str, Any]) -> dict[str, Any]:
        def _fake_ctor(**init_kwargs: Any) -> _FakeClient:
            client = _FakeClient(response_dict, **init_kwargs)
            captured["client"] = client
            return client

        groq_mod = ModuleType("groq")
        groq_mod.Groq = _fake_ctor  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "groq", groq_mod)
        return captured

    return _factory


def _completion(text: str, finish: str = "stop") -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": text},
                "finish_reason": finish,
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
    }


# ---------- auth ------------------------------------------------------------


def test_constructor_resolves_api_key_from_env_var(monkeypatch):
    from cantus.model.providers.groq import GroqChatModel

    monkeypatch.setenv("GROQ_API_KEY", "gsk-from-env")
    model = GroqChatModel(model_id="llama-3.3-70b-versatile")
    assert model._api_key == "gsk-from-env"


def test_constructor_explicit_api_key_wins_over_env(monkeypatch):
    from cantus.model.providers.groq import GroqChatModel

    monkeypatch.setenv("GROQ_API_KEY", "gsk-env")
    model = GroqChatModel(model_id="llama-3.3-70b-versatile", api_key="gsk-explicit")
    assert model._api_key == "gsk-explicit"


def test_missing_api_key_raises_missing_api_key_error_naming_groq_api_key(monkeypatch):
    from cantus.model.providers.groq import GroqChatModel

    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError) as exc:
        GroqChatModel(model_id="llama-3.3-70b-versatile")
    assert "GROQ_API_KEY" in str(exc.value)


# ---------- chat request shape + response translation -----------------------


def test_chat_sends_model_and_translated_messages(install_fake_groq):
    from cantus.model.providers.groq import GroqChatModel

    captured = install_fake_groq(_completion("hello"))
    model = GroqChatModel(model_id="llama-3.3-70b-versatile", api_key="gsk-x")
    resp = model.chat(
        [
            Message(role="system", content="be terse"),
            Message(role="user", content="hi"),
        ]
    )
    last = captured["client"].chat.completions.last_kwargs
    assert last["model"] == "llama-3.3-70b-versatile"
    # Groq wire is OpenAI-shaped: system stays in messages list (not a top-level kwarg).
    assert last["messages"] == [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "hi"},
    ]
    assert resp.message.content == "hello"
    assert resp.stop_reason == "end_turn"
    assert resp.usage == {"input_tokens": 3, "output_tokens": 2}


def test_chat_passes_tools_when_provided(install_fake_groq):
    from cantus.model.providers.groq import GroqChatModel

    captured = install_fake_groq(_completion("ok"))
    model = GroqChatModel(model_id="llama-3.3-70b-versatile", api_key="gsk-x")
    tools = [{"type": "function", "function": {"name": "search"}}]
    model.chat([Message(role="user", content="hi")], tools=tools)
    assert captured["client"].chat.completions.last_kwargs["tools"] == tools


# ---------- translator reuse — static guarantee -----------------------------


def test_adapter_reuses_openai_translator_functions():
    """The Groq adapter MUST import and call the OpenAI translator functions.

    Catches the "someone refactored Groq into its own translator" regression.
    Reuse is the explicit design decision (see design.md: "Groq adapter 透過 groq
    SDK 並複用 OpenAI 翻譯器").
    """
    import inspect

    from cantus.model.providers import groq as groq_adapter
    from cantus.model.providers._translate import (
        from_openai_response,
        to_openai_messages,
    )

    src = inspect.getsource(groq_adapter)
    assert "to_openai_messages" in src, "Groq adapter must use to_openai_messages"
    assert "from_openai_response" in src, "Groq adapter must use from_openai_response"
    # Sanity: the functions are the real OpenAI translators (not Groq-local copies).
    assert to_openai_messages.__module__ == "cantus.model.providers._translate"
    assert from_openai_response.__module__ == "cantus.model.providers._translate"


# ---------- protocol attributes ---------------------------------------------


def test_supports_tool_use_is_true(monkeypatch):
    from cantus.model.providers.groq import GroqChatModel

    monkeypatch.setenv("GROQ_API_KEY", "x")
    assert GroqChatModel(model_id="llama-3.3-70b-versatile").supports_tool_use is True


def test_model_id_attribute_is_set(monkeypatch):
    from cantus.model.providers.groq import GroqChatModel

    monkeypatch.setenv("GROQ_API_KEY", "x")
    assert GroqChatModel(model_id="my-model").model_id == "my-model"


# ---------- stream ----------------------------------------------------------


def test_stream_yields_only_text_deltas(monkeypatch):
    from cantus.model.providers.groq import GroqChatModel

    class _DeltaChunk:
        def __init__(self, content):
            self.choices = [SimpleNamespace(delta=SimpleNamespace(content=content))]

    def _fake_create(**kwargs):
        yield _DeltaChunk(None)
        yield _DeltaChunk("Hello ")
        yield _DeltaChunk("world")

    class _StreamClient:
        chat = SimpleNamespace(completions=SimpleNamespace(create=_fake_create))

    groq_mod = ModuleType("groq")
    groq_mod.Groq = lambda **kw: _StreamClient()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "groq", groq_mod)

    model = GroqChatModel(model_id="llama-3.3-70b-versatile", api_key="gsk-x")
    deltas = list(model.stream([Message(role="user", content="hi")]))
    assert deltas == ["Hello ", "world"]

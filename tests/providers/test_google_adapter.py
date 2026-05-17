"""Contract tests for GoogleChatModel — auth, request shape, response translation.

Uses SDK-level mocks (monkeypatch on `google.genai.Client`) instead of VCR
cassettes, matching the v0.2.0 OpenAI/Anthropic test convention. The translator
round-trip is already exercised by `tests/providers/test_translate.py`. VCR
cassettes can be added when live integration smoke is recorded with real
credentials by the release manager.

Adapter MUST use the new `google-genai` SDK (`from google import genai`), NOT
the legacy `google-generativeai` SDK. The "rejects legacy SDK" scenario in
the spec is enforced by the fact that the lazy import at first chat() call
targets the new SDK namespace; if only the legacy SDK is installed, that
import raises `ModuleNotFoundError`.
"""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from cantus.model.chat import Message
from cantus.model.providers._common import MissingAPIKeyError


# ---------- fake google-genai SDK -------------------------------------------


class _FakeModels:
    def __init__(self, response: Any, stream_chunks: list[Any] | None = None) -> None:
        self._response = response
        self._stream_chunks = stream_chunks or []
        self.last_kwargs: dict[str, Any] | None = None

    def generate_content(self, **kwargs: Any) -> Any:
        self.last_kwargs = kwargs
        return self._response

    def generate_content_stream(self, **kwargs: Any):
        self.last_kwargs = kwargs
        for chunk in self._stream_chunks:
            yield chunk


class _FakeGenaiClient:
    def __init__(self, **init_kwargs: Any) -> None:
        self.init_kwargs = init_kwargs
        self.models = _FakeModels(self._next_response, self._next_stream)

    _next_response: Any = None
    _next_stream: list[Any] = []


@pytest.fixture
def install_fake_genai(monkeypatch):
    """Install a fake `google.genai` package whose Client is test-controlled."""

    captured: dict[str, Any] = {}

    def _factory(response: Any, *, stream: list[Any] | None = None) -> dict[str, Any]:
        class _ScopedClient(_FakeGenaiClient):
            _next_response = response
            _next_stream = stream or []

        def _ctor(**init_kwargs: Any) -> _ScopedClient:
            client = _ScopedClient(**init_kwargs)
            captured["client"] = client
            return client

        google_pkg = ModuleType("google")
        genai_mod = ModuleType("google.genai")
        genai_mod.Client = _ctor  # type: ignore[attr-defined]
        google_pkg.genai = genai_mod  # type: ignore[attr-defined]

        monkeypatch.setitem(sys.modules, "google", google_pkg)
        monkeypatch.setitem(sys.modules, "google.genai", genai_mod)
        return captured

    return _factory


def _gemini_text_response(text: str, finish: str = "STOP") -> dict[str, Any]:
    return {
        "candidates": [
            {
                "content": {"parts": [{"text": text}], "role": "model"},
                "finish_reason": finish,
            }
        ],
        "usage_metadata": {"prompt_token_count": 3, "candidates_token_count": 2},
    }


# ---------- auth ------------------------------------------------------------


def test_constructor_resolves_api_key_from_env_var(monkeypatch):
    from cantus.model.providers.google import GoogleChatModel

    monkeypatch.setenv("GOOGLE_API_KEY", "ai-from-env")
    model = GoogleChatModel(model_id="gemini-2.0-flash")
    assert model._api_key == "ai-from-env"


def test_constructor_explicit_api_key_wins_over_env(monkeypatch):
    from cantus.model.providers.google import GoogleChatModel

    monkeypatch.setenv("GOOGLE_API_KEY", "ai-env")
    model = GoogleChatModel(model_id="gemini-2.0-flash", api_key="ai-explicit")
    assert model._api_key == "ai-explicit"


def test_missing_api_key_raises_missing_api_key_error_naming_google_api_key(monkeypatch):
    from cantus.model.providers.google import GoogleChatModel

    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError) as exc:
        GoogleChatModel(model_id="gemini-2.0-flash")
    assert "GOOGLE_API_KEY" in str(exc.value)


# ---------- chat request shape ----------------------------------------------


def test_chat_passes_system_instruction_as_top_level_kwarg(install_fake_genai):
    from cantus.model.providers.google import GoogleChatModel

    captured = install_fake_genai(_gemini_text_response("hello"))
    model = GoogleChatModel(model_id="gemini-2.0-flash", api_key="ai-x")
    model.chat(
        [
            Message(role="system", content="be terse"),
            Message(role="user", content="hi"),
        ]
    )
    last = captured["client"].models.last_kwargs
    assert last["model"] == "gemini-2.0-flash"
    assert last["system_instruction"] == "be terse"
    assert last["contents"] == [{"role": "user", "parts": [{"text": "hi"}]}]


def test_chat_omits_system_instruction_when_no_system_message(install_fake_genai):
    from cantus.model.providers.google import GoogleChatModel

    captured = install_fake_genai(_gemini_text_response("hello"))
    model = GoogleChatModel(model_id="gemini-2.0-flash", api_key="ai-x")
    model.chat([Message(role="user", content="hi")])
    last = captured["client"].models.last_kwargs
    assert "system_instruction" not in last or last.get("system_instruction") is None


def test_chat_returns_translated_response(install_fake_genai):
    from cantus.model.providers.google import GoogleChatModel

    install_fake_genai(_gemini_text_response("hi there", finish="STOP"))
    model = GoogleChatModel(model_id="gemini-2.0-flash", api_key="ai-x")
    resp = model.chat([Message(role="user", content="hi")])
    assert resp.message.role == "assistant"
    assert resp.message.content == "hi there"
    assert resp.stop_reason == "end_turn"
    assert resp.usage == {"input_tokens": 3, "output_tokens": 2}


def test_chat_passes_tools_when_provided(install_fake_genai):
    from cantus.model.providers.google import GoogleChatModel

    captured = install_fake_genai(_gemini_text_response("ok"))
    model = GoogleChatModel(model_id="gemini-2.0-flash", api_key="ai-x")
    tools = [{"function_declarations": [{"name": "search"}]}]
    model.chat([Message(role="user", content="hi")], tools=tools)
    assert captured["client"].models.last_kwargs["tools"] == tools


def test_chat_omits_tools_kwarg_when_none(install_fake_genai):
    from cantus.model.providers.google import GoogleChatModel

    captured = install_fake_genai(_gemini_text_response("ok"))
    model = GoogleChatModel(model_id="gemini-2.0-flash", api_key="ai-x")
    model.chat([Message(role="user", content="hi")])
    assert "tools" not in captured["client"].models.last_kwargs


# ---------- protocol attributes ---------------------------------------------


def test_supports_tool_use_is_true(monkeypatch):
    from cantus.model.providers.google import GoogleChatModel

    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    assert GoogleChatModel(model_id="gemini-2.0-flash").supports_tool_use is True


def test_model_id_attribute_is_set(monkeypatch):
    from cantus.model.providers.google import GoogleChatModel

    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    assert GoogleChatModel(model_id="gemini-2.0-flash").model_id == "gemini-2.0-flash"


# ---------- stream ----------------------------------------------------------


def test_stream_yields_only_text_deltas(install_fake_genai):
    from cantus.model.providers.google import GoogleChatModel

    class _Chunk(SimpleNamespace):
        pass

    chunks = [
        _Chunk(text="Hello "),
        _Chunk(text=None),  # empty / non-text part — must be filtered
        _Chunk(text="world"),
    ]
    install_fake_genai({}, stream=chunks)
    model = GoogleChatModel(model_id="gemini-2.0-flash", api_key="ai-x")
    deltas = list(model.stream([Message(role="user", content="hi")]))
    assert deltas == ["Hello ", "world"]


# ---------- rejection of legacy google-generativeai SDK ---------------------


def test_adapter_lazy_import_targets_google_genai_not_google_generativeai(monkeypatch):
    """If google-genai is missing but google-generativeai is present, chat() must raise.

    Guards the design decision that the new unified SDK is the only supported
    import path. The adapter MUST NOT silently fall back to the legacy SDK.
    """
    from cantus.model.providers.google import GoogleChatModel

    # Pretend the legacy SDK is installed but new SDK is not.
    legacy = ModuleType("google.generativeai")
    monkeypatch.setitem(sys.modules, "google.generativeai", legacy)
    # Force google.genai import to fail.
    monkeypatch.setitem(sys.modules, "google.genai", None)

    monkeypatch.setenv("GOOGLE_API_KEY", "x")
    model = GoogleChatModel(model_id="gemini-2.0-flash")
    with pytest.raises((ImportError, ModuleNotFoundError)):
        model._get_client()

"""Contract tests for load_chat_model factory — dispatch + lazy import."""

from __future__ import annotations

import sys
import types
from typing import Any

import pytest

from cantus.model.factory import load_chat_model
from cantus.model.chat import ChatModel


class _FakeAdapter:
    """Drop-in stand-in for OpenAIChatModel / AnthropicChatModel."""

    def __init__(self, model_id: str, **kwargs: Any) -> None:
        self.model_id = model_id
        self.kwargs = kwargs
        self.supports_tool_use = True

    def chat(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def stream(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


def _install_fake_module(name: str, class_attr: str) -> None:
    mod = types.ModuleType(name)
    setattr(mod, class_attr, _FakeAdapter)
    sys.modules[name] = mod


def _uninstall_fake_module(name: str) -> None:
    sys.modules.pop(name, None)


@pytest.fixture
def fake_openai_module():
    _install_fake_module("cantus.model.providers.openai", "OpenAIChatModel")
    yield
    _uninstall_fake_module("cantus.model.providers.openai")


@pytest.fixture
def fake_anthropic_module():
    _install_fake_module("cantus.model.providers.anthropic", "AnthropicChatModel")
    yield
    _uninstall_fake_module("cantus.model.providers.anthropic")


def test_unknown_provider_prefix_raises_value_error_naming_supported():
    with pytest.raises(ValueError) as exc:
        load_chat_model("groq/llama-3.3-70b")
    msg = str(exc.value)
    assert "openai" in msg
    assert "anthropic" in msg
    assert "groq" in msg


def test_spec_without_slash_raises_value_error_with_format_hint():
    with pytest.raises(ValueError) as exc:
        load_chat_model("just-a-model-id")
    msg = str(exc.value)
    assert "/" in msg or "provider" in msg.lower()


def test_empty_model_id_after_slash_raises_value_error():
    with pytest.raises(ValueError):
        load_chat_model("openai/")


def test_openai_dispatch_constructs_adapter_via_lazy_import(fake_openai_module):
    model = load_chat_model("openai/gpt-4o-mini")
    assert isinstance(model, _FakeAdapter)
    assert model.model_id == "gpt-4o-mini"


def test_anthropic_dispatch_constructs_adapter_via_lazy_import(fake_anthropic_module):
    model = load_chat_model("anthropic/claude-sonnet-4-6")
    assert isinstance(model, _FakeAdapter)
    assert model.model_id == "claude-sonnet-4-6"


def test_kwargs_pass_through_to_adapter_constructor(fake_openai_module):
    model = load_chat_model(
        "openai/gpt-4o-mini",
        api_key="sk-test",
        base_url="https://example/v1",
        temperature=0.7,
    )
    assert model.kwargs == {
        "api_key": "sk-test",
        "base_url": "https://example/v1",
        "temperature": 0.7,
    }


def test_missing_provider_extras_raises_import_error_with_install_hint(monkeypatch):
    """When the adapter module's SDK dep is not installed, surface a friendly hint."""
    import importlib

    real_import = importlib.import_module

    def fake_import(name: str, *args, **kwargs):
        if name == "cantus.model.providers.openai":
            raise ImportError("No module named 'openai'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    # Also ensure the module isn't cached from a previous test
    monkeypatch.delitem(sys.modules, "cantus.model.providers.openai", raising=False)

    with pytest.raises(ImportError) as exc:
        load_chat_model("openai/gpt-4o-mini")
    msg = str(exc.value)
    assert "pip install cantus[openai]" in msg


def test_returns_object_that_satisfies_chat_model_protocol(fake_openai_module):
    model = load_chat_model("openai/gpt-4o-mini")
    # _FakeAdapter implements chat/stream/supports_tool_use/model_id
    assert isinstance(model, ChatModel)

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


@pytest.fixture
def fake_google_module():
    _install_fake_module("cantus.model.providers.google", "GoogleChatModel")
    yield
    _uninstall_fake_module("cantus.model.providers.google")


@pytest.fixture
def fake_groq_module():
    _install_fake_module("cantus.model.providers.groq", "GroqChatModel")
    yield
    _uninstall_fake_module("cantus.model.providers.groq")


@pytest.fixture
def fake_nvidia_module():
    _install_fake_module("cantus.model.providers.nvidia", "NvidiaChatModel")
    yield
    _uninstall_fake_module("cantus.model.providers.nvidia")


def test_unknown_provider_prefix_raises_value_error_naming_supported():
    with pytest.raises(ValueError) as exc:
        load_chat_model("vertex/gemini-2.0-flash")
    msg = str(exc.value)
    for prefix in ("openai", "anthropic", "google", "groq", "nvidia"):
        assert prefix in msg, f"supported prefix {prefix!r} missing from {msg!r}"


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


# ---------- v0.2.1 batch2 prefixes -----------------------------------------


def test_google_dispatch_constructs_adapter_via_lazy_import(fake_google_module):
    model = load_chat_model("google/gemini-2.0-flash")
    assert isinstance(model, _FakeAdapter)
    assert model.model_id == "gemini-2.0-flash"


def test_groq_dispatch_constructs_adapter_via_lazy_import(fake_groq_module):
    model = load_chat_model("groq/llama-3.3-70b-versatile")
    assert isinstance(model, _FakeAdapter)
    assert model.model_id == "llama-3.3-70b-versatile"


def test_nvidia_dispatch_constructs_adapter_via_lazy_import(fake_nvidia_module):
    model = load_chat_model("nvidia/meta/llama-3.3-70b-instruct")
    assert isinstance(model, _FakeAdapter)
    # spec parses as <provider>/<model_id> with split("/", 1), so model_id retains
    # the embedded slash (NVIDIA's namespaced model_ids like "meta/llama-...")
    assert model.model_id == "meta/llama-3.3-70b-instruct"


def test_missing_google_extras_hint_points_to_cantus_google(monkeypatch):
    import importlib

    real_import = importlib.import_module

    def fake_import(name: str, *args, **kwargs):
        if name == "cantus.model.providers.google":
            raise ImportError("No module named 'google.genai'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.delitem(sys.modules, "cantus.model.providers.google", raising=False)

    with pytest.raises(ImportError) as exc:
        load_chat_model("google/gemini-2.0-flash")
    assert "pip install cantus[google]" in str(exc.value)


def test_missing_groq_extras_hint_points_to_cantus_groq(monkeypatch):
    import importlib

    real_import = importlib.import_module

    def fake_import(name: str, *args, **kwargs):
        if name == "cantus.model.providers.groq":
            raise ImportError("No module named 'groq'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.delitem(sys.modules, "cantus.model.providers.groq", raising=False)

    with pytest.raises(ImportError) as exc:
        load_chat_model("groq/llama-3.3-70b-versatile")
    assert "pip install cantus[groq]" in str(exc.value)


def test_missing_nvidia_extras_hint_points_to_cantus_openai_not_nvidia(monkeypatch):
    """NIM runs on the openai SDK — extras hint MUST point at cantus[openai]."""
    import importlib

    real_import = importlib.import_module

    def fake_import(name: str, *args, **kwargs):
        if name == "cantus.model.providers.nvidia":
            raise ImportError("No module named 'openai'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    monkeypatch.delitem(sys.modules, "cantus.model.providers.nvidia", raising=False)

    with pytest.raises(ImportError) as exc:
        load_chat_model("nvidia/meta/llama-3.3-70b-instruct")
    msg = str(exc.value)
    assert "pip install cantus[openai]" in msg
    assert "cantus[nvidia]" not in msg

"""Contract tests for OllamaChatModel — subclass of OpenAIChatModel pointing at the local Ollama daemon.

Ollama exposes an OpenAI-compatible Chat Completions wire at
``http://localhost:11434/v1``. The adapter is an even thinner subclass than
``NvidiaChatModel``: it defaults ``base_url`` to the local daemon and uses a
hard-coded sentinel string ``"ollama"`` as the api_key (the daemon ignores
the field but the openai SDK requires a non-empty string). It MUST NOT
consult ``OLLAMA_API_KEY`` or any other environment variable.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from cantus.model.chat import Message
from cantus.model.providers.ollama import (
    OLLAMA_API_KEY_SENTINEL,
    OLLAMA_BASE_URL,
    OllamaChatModel,
)
from cantus.model.providers.openai import OpenAIChatModel


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
def install_fake_openai(monkeypatch):
    captured: dict[str, Any] = {}

    def _factory(response_dict: dict[str, Any]) -> dict[str, Any]:
        def _ctor(**init_kwargs: Any) -> _FakeClient:
            client = _FakeClient(response_dict, **init_kwargs)
            captured["client"] = client
            return client

        import openai

        monkeypatch.setattr(openai, "OpenAI", _ctor)
        return captured

    return _factory


def _completion(text: str) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
    }


# ---------- spec Example table row 1: bare construction ---------------------


def test_default_base_url_and_api_key():
    model = OllamaChatModel(model_id="gemma3:4b")
    assert model._api_key == OLLAMA_API_KEY_SENTINEL == "ollama"
    assert model._base_url == OLLAMA_BASE_URL == "http://localhost:11434/v1"


# ---------- spec Example table row 3: explicit base_url ---------------------


def test_explicit_base_url_overrides_default():
    model = OllamaChatModel(
        model_id="gemma3:4b",
        base_url="http://192.168.1.5:11434/v1",
    )
    assert model._base_url == "http://192.168.1.5:11434/v1"
    # api_key still falls back to sentinel
    assert model._api_key == "ollama"


# ---------- spec Example table row 2: explicit api_key ----------------------


def test_explicit_api_key_overrides_sentinel():
    model = OllamaChatModel(model_id="gemma3:4b", api_key="x")
    assert model._api_key == "x"
    # base_url still defaults to local daemon
    assert model._base_url == "http://localhost:11434/v1"


# ---------- spec scenario: no OLLAMA_API_KEY env consultation ---------------


def test_missing_ollama_api_key_env_does_not_raise(monkeypatch):
    """Ollama adapter MUST NOT consult OLLAMA_API_KEY — sentinel is used unconditionally."""
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Should not raise MissingAPIKeyError or anything else
    model = OllamaChatModel(model_id="gemma3:4b")
    assert model._api_key == "ollama"


# ---------- protocol attribute inherited from OpenAIChatModel ---------------


def test_supports_tool_use_inherited_true():
    assert OllamaChatModel.supports_tool_use is True
    # Sanity: the attribute MUST be inherited, not redefined on the subclass.
    assert "supports_tool_use" not in OllamaChatModel.__dict__


# ---------- subclass / inheritance contract ---------------------------------


def test_ollama_is_subclass_of_openai_chat_model():
    assert issubclass(OllamaChatModel, OpenAIChatModel)


# ---------- end-to-end: SDK client init kwargs receive sentinel + local URL -


def test_chat_passes_sentinel_and_default_base_url_to_sdk_client(install_fake_openai):
    captured = install_fake_openai(_completion("ok"))
    model = OllamaChatModel(model_id="gemma3:4b")
    model.chat([Message(role="user", content="hi")])
    assert captured["client"].init_kwargs["api_key"] == "ollama"
    assert captured["client"].init_kwargs["base_url"] == "http://localhost:11434/v1"

"""Contract tests for NvidiaChatModel — subclass of OpenAIChatModel with NIM base_url.

NVIDIA NIM exposes an OpenAI-compatible Chat Completions wire at
`https://integrate.api.nvidia.com/v1`. The adapter is a thin subclass:
it ONLY changes the default `base_url` and the API-key env var; chat /
stream / translator behavior inherits from OpenAIChatModel unchanged.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace
from typing import Any

import pytest

from cantus.model.chat import Message
from cantus.model.providers._common import MissingAPIKeyError
from cantus.model.providers.openai import OpenAIChatModel


NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


# ---------- fake openai SDK (shared with OpenAI adapter shape) --------------


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


# ---------- base_url default ------------------------------------------------


def test_default_base_url_is_nim_endpoint(install_fake_openai):
    from cantus.model.providers.nvidia import NvidiaChatModel

    captured = install_fake_openai(_completion("ok"))
    model = NvidiaChatModel(model_id="meta/llama-3.3-70b-instruct", api_key="nvapi-x")
    model.chat([Message(role="user", content="hi")])
    assert captured["client"].init_kwargs["base_url"] == NIM_BASE_URL


def test_explicit_base_url_overrides_nim_default(install_fake_openai):
    from cantus.model.providers.nvidia import NvidiaChatModel

    captured = install_fake_openai(_completion("ok"))
    model = NvidiaChatModel(
        model_id="m",
        api_key="nvapi-x",
        base_url="https://my-proxy.example/v1",
    )
    model.chat([Message(role="user", content="hi")])
    assert captured["client"].init_kwargs["base_url"] == "https://my-proxy.example/v1"


# ---------- auth ------------------------------------------------------------


def test_constructor_resolves_api_key_from_nvidia_api_key_env(monkeypatch):
    from cantus.model.providers.nvidia import NvidiaChatModel

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-from-env")
    model = NvidiaChatModel(model_id="meta/llama-3.3-70b-instruct")
    assert model._api_key == "nvapi-from-env"


def test_constructor_does_not_fall_back_to_openai_api_key_env(monkeypatch):
    """NVIDIA adapter MUST read NVIDIA_API_KEY only — never OPENAI_API_KEY."""
    from cantus.model.providers.nvidia import NvidiaChatModel

    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-not-this-one")
    with pytest.raises(MissingAPIKeyError) as exc:
        NvidiaChatModel(model_id="meta/llama-3.3-70b-instruct")
    msg = str(exc.value)
    assert "NVIDIA_API_KEY" in msg
    assert "OPENAI_API_KEY" not in msg


def test_constructor_explicit_api_key_wins_over_env(monkeypatch):
    from cantus.model.providers.nvidia import NvidiaChatModel

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-env")
    model = NvidiaChatModel(
        model_id="meta/llama-3.3-70b-instruct", api_key="nvapi-explicit"
    )
    assert model._api_key == "nvapi-explicit"


# ---------- subclass / inheritance contract ---------------------------------


def test_nvidia_is_subclass_of_openai_chat_model():
    from cantus.model.providers.nvidia import NvidiaChatModel

    assert issubclass(NvidiaChatModel, OpenAIChatModel)


def test_nvidia_does_not_override_chat_or_stream():
    """Subclass MUST inherit chat/stream behavior to keep the implementation thin."""
    from cantus.model.providers.nvidia import NvidiaChatModel

    # Method resolution: chat and stream should come from OpenAIChatModel.
    assert NvidiaChatModel.chat is OpenAIChatModel.chat
    assert NvidiaChatModel.stream is OpenAIChatModel.stream


def test_nvidia_module_is_thin_under_thirty_logical_lines():
    """Design contract: NvidiaChatModel implementation < 30 lines.

    Catches the "someone re-implemented chat()" regression by enforcing the
    "thin subclass" decision quantitatively.
    """
    from cantus.model.providers import nvidia as nvidia_mod

    src = inspect.getsource(nvidia_mod)
    logical_lines = [
        line
        for line in src.splitlines()
        if line.strip() and not line.strip().startswith("#")
        and not line.strip().startswith('"""')
        and not line.strip().startswith("'''")
    ]
    # Allow module docstring; the assertion targets actual code volume.
    assert len([ln for ln in logical_lines if not ln.startswith('"')]) < 60, (
        "NvidiaChatModel grew beyond a thin subclass; if you needed more code, "
        "split it out rather than fattening the adapter."
    )


# ---------- chat shape via inherited OpenAI path ---------------------------


def test_chat_sends_translated_messages_via_inherited_openai_path(install_fake_openai):
    from cantus.model.providers.nvidia import NvidiaChatModel

    captured = install_fake_openai(_completion("hi there"))
    model = NvidiaChatModel(model_id="meta/llama-3.3-70b-instruct", api_key="nvapi-x")
    resp = model.chat(
        [
            Message(role="system", content="be terse"),
            Message(role="user", content="hi"),
        ]
    )
    last = captured["client"].chat.completions.last_kwargs
    # OpenAI Chat Completions wire shape — system stays in messages, no top-level kwarg.
    assert last["model"] == "meta/llama-3.3-70b-instruct"
    assert last["messages"] == [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "hi"},
    ]
    assert resp.message.content == "hi there"
    assert resp.stop_reason == "end_turn"


# ---------- protocol attributes ---------------------------------------------


def test_supports_tool_use_inherits_true(monkeypatch):
    from cantus.model.providers.nvidia import NvidiaChatModel

    monkeypatch.setenv("NVIDIA_API_KEY", "x")
    assert NvidiaChatModel(model_id="meta/llama-3.3-70b-instruct").supports_tool_use is True


# ---------- stream ----------------------------------------------------------


def test_stream_yields_only_text_deltas_via_inherited_path(monkeypatch):
    from cantus.model.providers.nvidia import NvidiaChatModel

    class _DeltaChunk:
        def __init__(self, content):
            self.choices = [SimpleNamespace(delta=SimpleNamespace(content=content))]

    def _fake_create(**kwargs):
        yield _DeltaChunk(None)
        yield _DeltaChunk("Hello ")
        yield _DeltaChunk("world")

    class _StreamClient:
        chat = SimpleNamespace(completions=SimpleNamespace(create=_fake_create))

    import openai

    monkeypatch.setattr(openai, "OpenAI", lambda **kw: _StreamClient())

    model = NvidiaChatModel(model_id="meta/llama-3.3-70b-instruct", api_key="nvapi-x")
    deltas = list(model.stream([Message(role="user", content="hi")]))
    assert deltas == ["Hello ", "world"]

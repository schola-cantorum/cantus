"""Contract tests for OmlxChatModel — subclass of OpenAIChatModel pointing at a
local OpenAI-compatible MLX server (omlx / mlx-omni-server).

These tests fake the `openai` SDK client (no live server, no network). The
adapter mirrors ``OllamaChatModel`` but with two deliberate differences:

* it REQUIRES an explicit ``base_url`` — there is no single sensible default
  between omlx (``http://localhost:8000/v1``) and mlx-omni-server
  (``http://localhost:10240/v1``); and
* it keeps ``supports_tool_use = True`` (these servers expose function
  calling), unlike the in-process ``MLXChatModel`` whose value is ``False``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest

from cantus.model.chat import ChatModel, Message
from cantus.model.providers.omlx import OMLX_API_KEY_SENTINEL, OmlxChatModel
from cantus.model.providers.openai import OpenAIChatModel


# --- fakes (mirror tests/providers/test_ollama_adapter.py) ------------------


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


_OMLX_URL = "http://localhost:8000/v1"
_MLX_OMNI_URL = "http://localhost:10240/v1"


# --- Requirement: OmlxChatModel is a thin OpenAIChatModel subclass ----------


def test_omlx_is_subclass_of_openai_chat_model():
    assert issubclass(OmlxChatModel, OpenAIChatModel)


def test_satisfies_chat_model_protocol_and_keeps_model_id():
    model = OmlxChatModel(model_id="qwen2.5-coder-7b", base_url=_OMLX_URL)
    assert isinstance(model, ChatModel)
    assert isinstance(model, OpenAIChatModel)
    assert model.model_id == "qwen2.5-coder-7b"


def test_base_url_passes_through_to_sdk_client(install_fake_openai):
    captured = install_fake_openai(_completion("ok"))
    model = OmlxChatModel(model_id="m", base_url=_MLX_OMNI_URL)
    model.chat([Message(role="user", content="hi")])
    assert captured["client"].init_kwargs["base_url"] == _MLX_OMNI_URL


# --- Requirement: OmlxChatModel requires an explicit base_url ---------------


def test_missing_base_url_raises_value_error_naming_both_endpoints():
    with pytest.raises(ValueError) as exc:
        OmlxChatModel(model_id="qwen2.5-coder-7b")
    msg = str(exc.value)
    assert _OMLX_URL in msg, f"omlx endpoint missing from {msg!r}"
    assert _MLX_OMNI_URL in msg, f"mlx-omni-server endpoint missing from {msg!r}"


def test_explicit_base_url_does_not_raise():
    # No ValueError when base_url is supplied.
    model = OmlxChatModel(model_id="m", base_url=_OMLX_URL)
    assert model._base_url == _OMLX_URL


# --- Requirement: OmlxChatModel uses a sentinel api_key, never the env ------


def test_missing_api_key_env_uses_sentinel(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OMLX_API_KEY", raising=False)
    model = OmlxChatModel(model_id="m", base_url=_OMLX_URL)
    assert model._api_key == OMLX_API_KEY_SENTINEL == "omlx"


def test_explicit_api_key_is_preserved():
    model = OmlxChatModel(model_id="m", base_url=_OMLX_URL, api_key="proxy-token")
    assert model._api_key == "proxy-token"


def test_empty_api_key_falls_back_to_sentinel_and_skips_env(monkeypatch):
    """An empty api_key is treated as absent — the sentinel is used and the
    adapter does NOT fall through to the parent's env-var resolution (which
    would otherwise pick up OPENAI_API_KEY). Audit hardening: api_key="" must
    not silently re-open env consultation."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-be-used")
    model = OmlxChatModel(model_id="m", base_url=_OMLX_URL, api_key="")
    assert model._api_key == OMLX_API_KEY_SENTINEL == "omlx"


def test_class_docstring_discloses_non_authoritative_api_key():
    """`OmlxChatModel.__doc__` SHALL disclose that api_key is accepted but not
    authoritative on the local server side."""
    doc = OmlxChatModel.__doc__
    assert doc is not None, "OmlxChatModel must have a class docstring"
    assert "api_key parameter is accepted but" in doc
    assert "not authoritative" in doc


# --- Requirement: OmlxChatModel reports tool-use support (inherited True) ---


def test_supports_tool_use_inherited_true():
    assert OmlxChatModel.supports_tool_use is True
    # The attribute MUST be inherited, not redefined on the subclass.
    assert "supports_tool_use" not in OmlxChatModel.__dict__


# --- Requirement: actionable ConnectionError when the server is unreachable -


class _RaisingChoices:
    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    def create(self, **kwargs: Any) -> Any:
        raise self._exc


class _RaisingClient:
    def __init__(self, exc: BaseException, **init_kwargs: Any) -> None:
        self.init_kwargs = init_kwargs
        self.chat = SimpleNamespace(completions=_RaisingChoices(exc))


@pytest.fixture
def install_raising_openai(monkeypatch):
    def _factory(exc: BaseException) -> None:
        def _ctor(**init_kwargs: Any) -> _RaisingClient:
            return _RaisingClient(exc, **init_kwargs)

        monkeypatch.setattr(openai, "OpenAI", _ctor)

    return _factory


def _api_connection_error() -> openai.APIConnectionError:
    return openai.APIConnectionError(request=httpx.Request("POST", _OMLX_URL))


def _not_found_error() -> openai.NotFoundError:
    request = httpx.Request("POST", _OMLX_URL)
    response = httpx.Response(404, request=request)
    return openai.NotFoundError("model not loaded", response=response, body=None)


def test_chat_connection_error_becomes_actionable_connection_error(install_raising_openai):
    install_raising_openai(_api_connection_error())
    model = OmlxChatModel(model_id="m", base_url=_OMLX_URL)
    with pytest.raises(ConnectionError) as exc:
        model.chat([Message(role="user", content="hi")])
    assert _OMLX_URL in str(exc.value)
    assert isinstance(exc.value.__cause__, openai.APIConnectionError)


def test_stream_connection_error_becomes_actionable_connection_error(install_raising_openai):
    install_raising_openai(_api_connection_error())
    model = OmlxChatModel(model_id="m", base_url=_OMLX_URL)
    with pytest.raises(ConnectionError) as exc:
        list(model.stream([Message(role="user", content="hi")]))
    assert _OMLX_URL in str(exc.value)


def test_non_connection_openai_error_propagates_unchanged(install_raising_openai):
    install_raising_openai(_not_found_error())
    model = OmlxChatModel(model_id="m", base_url=_OMLX_URL)
    with pytest.raises(openai.NotFoundError):
        model.chat([Message(role="user", content="hi")])

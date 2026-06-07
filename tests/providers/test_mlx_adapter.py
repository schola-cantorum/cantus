"""Contract tests for MLXChatModel — fake `mlx_lm`, no real model load.

MLX (`mlx-lm`) is Apple-Silicon-only and pulls heavyweight native wheels, so
these tests never import the real package. Instead each test installs a fake
`mlx_lm` module (with `load` / `generate` / `stream_generate`) into
`sys.modules` *before* importing the adapter, then imports
`cantus.model.providers.mlx` fresh so its module-level `import mlx_lm` binds to
the fake. This mirrors the `tests/test_factory.py` fake-module pattern and lets
the full contract run on any platform / CI runner.
"""

from __future__ import annotations

import importlib
import platform
import sys
import types
from typing import Any

import pytest

from cantus.model.chat import ChatModel, ChatResponse, Message

ADAPTER = "cantus.model.providers.mlx"


class _FakeTokenizer:
    """Stand-in for an mlx-lm tokenizer exposing `apply_chat_template`."""

    def __init__(self) -> None:
        self.calls: list[Any] = []

    def apply_chat_template(
        self,
        conversation: list[dict[str, str]],
        add_generation_prompt: bool = False,
        **kwargs: Any,
    ) -> str:
        self.calls.append((conversation, add_generation_prompt))
        return "PROMPT:" + "|".join(turn["content"] for turn in conversation)


def _make_fake_mlx_lm() -> types.ModuleType:
    """Build a fake `mlx_lm` module whose generation behavior is mutable."""
    mod = types.ModuleType("mlx_lm")
    state: dict[str, Any] = {
        "load_calls": [],
        "gen_text": "hello from mlx",
        "stream_deltas": ["foo", "bar"],
        "tokenizer": _FakeTokenizer(),
    }

    def load(model_id: str) -> tuple[str, _FakeTokenizer]:
        state["load_calls"].append(model_id)
        return ("FAKE_MODEL", state["tokenizer"])

    def generate(model: Any, tokenizer: Any, prompt: Any, **kwargs: Any) -> str:
        state["last_generate"] = {"prompt": prompt, "kwargs": kwargs}
        return state["gen_text"]

    def stream_generate(model: Any, tokenizer: Any, prompt: Any, **kwargs: Any) -> Any:
        state["last_stream"] = {"prompt": prompt, "kwargs": kwargs}
        for delta in state["stream_deltas"]:
            yield delta

    mod.load = load  # type: ignore[attr-defined]
    mod.generate = generate  # type: ignore[attr-defined]
    mod.stream_generate = stream_generate  # type: ignore[attr-defined]
    mod._state = state  # type: ignore[attr-defined]
    return mod


@pytest.fixture
def mlx_env(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """Install a fake `mlx_lm` and return the freshly-imported adapter module."""
    fake = _make_fake_mlx_lm()
    monkeypatch.setitem(sys.modules, "mlx_lm", fake)
    monkeypatch.delitem(sys.modules, ADAPTER, raising=False)
    module = importlib.import_module(ADAPTER)
    return types.SimpleNamespace(module=module, state=fake._state)  # type: ignore[attr-defined]


# --- Requirement: MLXChatModel implements the Tier 2 ChatModel Protocol -----


def test_satisfies_chat_model_protocol_shape(mlx_env: types.SimpleNamespace) -> None:
    inst = mlx_env.module.MLXChatModel(
        model_id="mlx-community/Mistral-7B-Instruct-v0.3-4bit"
    )
    assert isinstance(inst, ChatModel)
    assert inst.model_id == "mlx-community/Mistral-7B-Instruct-v0.3-4bit"


def test_construction_does_not_load_weights_eagerly(
    mlx_env: types.SimpleNamespace,
) -> None:
    mlx_env.module.MLXChatModel(model_id="m")
    assert mlx_env.state["load_calls"] == []


def test_chat_returns_chat_response_carrying_generated_text(
    mlx_env: types.SimpleNamespace,
) -> None:
    mlx_env.state["gen_text"] = "hello from mlx"
    model = mlx_env.module.MLXChatModel(model_id="m")
    response = model.chat([Message(role="user", content="hi")])
    assert isinstance(response, ChatResponse)
    assert response.message.role == "assistant"
    assert response.message.content == "hello from mlx"
    assert response.stop_reason == "end_turn"


def test_stream_yields_text_deltas_in_order(
    mlx_env: types.SimpleNamespace,
) -> None:
    mlx_env.state["stream_deltas"] = ["foo", "bar"]
    model = mlx_env.module.MLXChatModel(model_id="m")
    assert list(model.stream([Message(role="user", content="hi")])) == ["foo", "bar"]


# --- Requirement: reports no tool-use support and rejects tool arguments -----

_NO_TOOLS = "MLXChatModel does not support tool use"
_TOOLS = [{"type": "function", "function": {"name": "f"}}]


def test_supports_tool_use_is_false(mlx_env: types.SimpleNamespace) -> None:
    assert mlx_env.module.MLXChatModel(model_id="m").supports_tool_use is False


def test_chat_with_non_empty_tools_raises_not_implemented(
    mlx_env: types.SimpleNamespace,
) -> None:
    model = mlx_env.module.MLXChatModel(model_id="m")
    with pytest.raises(NotImplementedError) as exc:
        model.chat([Message(role="user", content="hi")], tools=_TOOLS)
    assert _NO_TOOLS in str(exc.value)


def test_stream_with_non_empty_tools_raises_not_implemented(
    mlx_env: types.SimpleNamespace,
) -> None:
    model = mlx_env.module.MLXChatModel(model_id="m")
    with pytest.raises(NotImplementedError) as exc:
        list(model.stream([Message(role="user", content="hi")], tools=_TOOLS))
    assert _NO_TOOLS in str(exc.value)


# --- Requirement: actionable error when mlx-lm unavailable / wrong platform --


def _import_adapter_with_unavailable_mlx(
    monkeypatch: pytest.MonkeyPatch,
    *,
    platform_name: str,
    machine: str,
) -> None:
    """Force `import mlx_lm` to fail on the given simulated platform, then
    import the adapter fresh so its module-level guard runs."""
    monkeypatch.setattr(sys, "platform", platform_name)
    monkeypatch.setattr(platform, "machine", lambda: machine)
    # A `None` entry makes `import mlx_lm` raise ImportError deterministically,
    # even if the real package happens to be installed in this environment.
    monkeypatch.setitem(sys.modules, "mlx_lm", None)
    monkeypatch.delitem(sys.modules, ADAPTER, raising=False)
    importlib.import_module(ADAPTER)


def test_missing_mlx_lm_yields_actionable_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ImportError) as exc:
        _import_adapter_with_unavailable_mlx(
            monkeypatch, platform_name="darwin", machine="arm64"
        )
    assert "pip install cantus[mlx]" in str(exc.value)


def test_non_apple_silicon_platform_message_names_the_constraint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ImportError) as exc:
        _import_adapter_with_unavailable_mlx(
            monkeypatch, platform_name="linux", machine="x86_64"
        )
    message = str(exc.value)
    assert "pip install cantus[mlx]" in message
    assert "Apple Silicon" in message
    assert "arm64" in message

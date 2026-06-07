"""MLX (`mlx-lm`) in-process ChatModel adapter — Apple Silicon only.

Unlike the OpenAI-compatible adapters, mlx-lm is *not* a wire protocol: it
loads local weights with `mlx_lm.load(model_id) -> (model, tokenizer)` and
generates text with `mlx_lm.generate` / `mlx_lm.stream_generate`. There is no
client, endpoint, or API key, so `MLXChatModel` implements the Tier 2
`ChatModel` Protocol directly rather than subclassing `OpenAIChatModel`.

This release reports `supports_tool_use = False`: mlx-lm has no native
structured tool-call output, so `chat` / `stream` reject a non-empty `tools`
argument loudly instead of silently degrading.
"""

from __future__ import annotations

import platform
import sys
from collections.abc import Iterator
from typing import Any

from cantus.model.chat import ChatResponse, Message

try:
    import mlx_lm
except ImportError as exc:  # pragma: no cover - exercised via importlib in tests
    _hint = "MLXChatModel requires the mlx-lm package. Run: pip install cantus[mlx]"
    if sys.platform != "darwin" or platform.machine() != "arm64":
        _hint += (
            " — note: MLX is supported only on Apple Silicon (macOS arm64); "
            f"the current platform is not arm64 ({sys.platform}/{platform.machine()})."
        )
    raise ImportError(_hint) from exc

_NO_TOOL_USE = (
    "MLXChatModel does not support tool use in this release "
    "(mlx-lm has no native structured tool-call output)"
)


class MLXChatModel:
    """Tier 2 adapter running mlx-lm in-process on Apple Silicon.

    Model weights load lazily on the first `chat` / `stream` call so that
    construction performs no heavyweight I/O.
    """

    supports_tool_use = False

    def __init__(self, model_id: str, **kwargs: Any) -> None:
        self.model_id = model_id
        self.supports_tool_use = False
        self._kwargs = kwargs
        self._model: Any = None
        self._tokenizer: Any = None

    def _ensure_loaded(self) -> None:
        if self._model is None:
            self._model, self._tokenizer = mlx_lm.load(self.model_id)

    def _build_prompt(self, messages: list[Message]) -> Any:
        conversation = [{"role": m.role, "content": m.content} for m in messages]
        return self._tokenizer.apply_chat_template(
            conversation, add_generation_prompt=True
        )

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        if tools:
            raise NotImplementedError(_NO_TOOL_USE)
        self._ensure_loaded()
        prompt = self._build_prompt(messages)
        text = mlx_lm.generate(self._model, self._tokenizer, prompt, **kwargs)
        return ChatResponse(
            message=Message(role="assistant", content=str(text)),
            stop_reason="end_turn",
        )

    def stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        if tools:
            raise NotImplementedError(_NO_TOOL_USE)
        self._ensure_loaded()
        prompt = self._build_prompt(messages)
        for chunk in mlx_lm.stream_generate(
            self._model, self._tokenizer, prompt, **kwargs
        ):
            # Real mlx-lm yields GenerationResponse objects carrying the
            # incremental text in `.text`; the contract fakes yield bare
            # strings. `getattr(..., chunk)` handles both.
            yield str(getattr(chunk, "text", chunk))

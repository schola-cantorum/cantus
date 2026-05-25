"""Ollama adapter — thin subclass of OpenAIChatModel targeting the local daemon.

Ollama exposes an OpenAI-compatible Chat Completions wire at
``http://localhost:11434/v1`` and ignores any API key field. The adapter
therefore (1) defaults ``base_url`` to the local daemon endpoint and
(2) uses the hard-coded sentinel string ``"ollama"`` as the api_key
because the openai SDK requires a non-empty string. It does NOT consult
``OLLAMA_API_KEY`` or any other environment variable — the field is
purely cosmetic on the Ollama side.

Connection failures (daemon not running, wrong port) surface as the
underlying ``openai.APIConnectionError`` with a long httpx stack trace
that is unhelpful to students. ``chat()`` and ``stream()`` are therefore
overridden to re-raise as ``ConnectionError`` with an actionable message
naming the daemon URL, ``ollama serve``, and the install link. All other
openai exception types propagate unchanged so callers can distinguish
"daemon down" from "model not pulled" (``openai.NotFoundError``) or
"auth misconfigured" (``openai.AuthenticationError``).

Because the runtime SDK is ``openai``, there is intentionally NO
``cantus[ollama]`` extras dependency closure beyond a documentary alias;
install via ``pip install cantus[openai]`` (or the documentary
``pip install cantus[ollama]`` alias, which resolves to the same set).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import openai

from cantus.model.chat import ChatResponse, Message
from cantus.model.providers.openai import OpenAIChatModel


OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_API_KEY_SENTINEL = "ollama"


class OllamaChatModel(OpenAIChatModel):
    """Tier 2 adapter for the local Ollama daemon (OpenAI-compatible)."""

    def __init__(
        self,
        model_id: str,
        api_key: str | None = None,
        base_url: str | None = None,
        **client_kwargs: Any,
    ) -> None:
        resolved_key = api_key if api_key is not None else OLLAMA_API_KEY_SENTINEL
        resolved_url = base_url if base_url is not None else OLLAMA_BASE_URL
        super().__init__(
            model_id=model_id,
            api_key=resolved_key,
            base_url=resolved_url,
            **client_kwargs,
        )

    def _connection_error_message(self) -> str:
        return (
            f"Cannot reach Ollama daemon at {self._base_url}. "
            f"Is `ollama serve` running? "
            f"Install: https://ollama.com/download — "
            f"then `ollama pull <model>` before retrying."
        )

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        try:
            return super().chat(messages, tools=tools, **kwargs)
        except openai.APIConnectionError as exc:
            raise ConnectionError(self._connection_error_message()) from exc

    def stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        try:
            yield from super().stream(messages, tools=tools, **kwargs)
        except openai.APIConnectionError as exc:
            raise ConnectionError(self._connection_error_message()) from exc

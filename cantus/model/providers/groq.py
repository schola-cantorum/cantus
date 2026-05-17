"""Groq adapter for Tier 2 ChatModel.

Groq's `client.chat.completions.create` exposes an OpenAI-compatible wire
shape, so this adapter directly reuses `to_openai_messages` /
`from_openai_response` from `_translate.py` — there is intentionally NO
`to_groq_messages`. SDK pin (`groq>=0.11,<1`) gives a per-cassette
re-recording cadence as Groq evolves the tool-use schema.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from cantus.model.chat import ChatResponse, Message
from cantus.model.providers._common import resolve_api_key
from cantus.model.providers._translate import (
    from_openai_response,
    to_openai_messages,
)


class GroqChatModel:
    """Tier 2 adapter for the Groq Chat Completions API."""

    supports_tool_use = True

    def __init__(
        self,
        model_id: str,
        api_key: str | None = None,
        **client_kwargs: Any,
    ) -> None:
        self.model_id = model_id
        self._api_key = resolve_api_key(api_key, "GROQ_API_KEY")
        self._client_kwargs = client_kwargs
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from groq import Groq  # type: ignore[import-not-found]

            self._client = Groq(api_key=self._api_key, **self._client_kwargs)
        return self._client

    def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        client = self._get_client()
        request_kwargs: dict[str, Any] = {
            "model": self.model_id,
            "messages": to_openai_messages(messages),
            **kwargs,
        }
        if tools:
            request_kwargs["tools"] = tools
        raw = client.chat.completions.create(**request_kwargs)
        return from_openai_response(raw)

    def stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        client = self._get_client()
        request_kwargs: dict[str, Any] = {
            "model": self.model_id,
            "messages": to_openai_messages(messages),
            "stream": True,
            **kwargs,
        }
        if tools:
            request_kwargs["tools"] = tools
        for chunk in client.chat.completions.create(**request_kwargs):
            choice = chunk.choices[0] if chunk.choices else None
            if choice is None:
                continue
            delta = getattr(choice, "delta", None)
            if delta is None:
                continue
            content = getattr(delta, "content", None)
            if content:
                yield content

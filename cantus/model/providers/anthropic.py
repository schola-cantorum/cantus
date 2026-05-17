"""Anthropic Messages adapter for Tier 2 ChatModel.

Anthropic puts the system prompt in a top-level `system=` kwarg rather than
inside `messages`, so the adapter relies on `to_anthropic_messages()` to
extract it before constructing the request. Tool use uses content-block
shapes (`type: "tool_use"` / `type: "tool_result"`) — the translator hides
that from callers; cantus `Message` + `ToolCall` are the API.

`max_tokens` is required by the Anthropic API. Callers MUST pass it via
kwargs; the adapter does not silently inject a default.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from cantus.model.chat import ChatResponse, Message
from cantus.model.providers._common import resolve_api_key
from cantus.model.providers._translate import (
    from_anthropic_response,
    to_anthropic_messages,
)


class AnthropicChatModel:
    """Tier 2 adapter for the Anthropic Messages API."""

    supports_tool_use = True

    def __init__(
        self,
        model_id: str,
        api_key: str | None = None,
        **client_kwargs: Any,
    ) -> None:
        self.model_id = model_id
        self._api_key = resolve_api_key(api_key, "ANTHROPIC_API_KEY")
        self._client_kwargs = client_kwargs
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from anthropic import Anthropic  # type: ignore[import-not-found]

            self._client = Anthropic(api_key=self._api_key, **self._client_kwargs)
        return self._client

    def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        client = self._get_client()
        system, translated = to_anthropic_messages(messages)
        request_kwargs: dict[str, Any] = {
            "model": self.model_id,
            "messages": translated,
            **kwargs,
        }
        if system is not None:
            request_kwargs["system"] = system
        if tools:
            request_kwargs["tools"] = tools
        raw = client.messages.create(**request_kwargs)
        return from_anthropic_response(raw)

    def stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        client = self._get_client()
        system, translated = to_anthropic_messages(messages)
        request_kwargs: dict[str, Any] = {
            "model": self.model_id,
            "messages": translated,
            **kwargs,
        }
        if system is not None:
            request_kwargs["system"] = system
        if tools:
            request_kwargs["tools"] = tools
        with client.messages.stream(**request_kwargs) as stream:
            for text in stream.text_stream:
                yield text

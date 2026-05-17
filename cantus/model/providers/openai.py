"""OpenAI Chat Completions adapter for Tier 2 ChatModel.

Locks to Chat Completions (`client.chat.completions.create`) — NOT the
Responses API — because Responses message/tool shapes do not yet round-trip
1:1 with the cross-provider `Message` dataclass. Revisit in v0.3.x.

`base_url` is exposed from day one so v0.2.1 NVIDIA NIM (OpenAI-compatible
endpoint at `https://integrate.api.nvidia.com/v1`) can subclass or proxy
this adapter without an API change.
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


class OpenAIChatModel:
    """Tier 2 adapter for OpenAI Chat Completions."""

    supports_tool_use = True

    def __init__(
        self,
        model_id: str,
        api_key: str | None = None,
        base_url: str | None = None,
        **client_kwargs: Any,
    ) -> None:
        self.model_id = model_id
        self._api_key = resolve_api_key(api_key, "OPENAI_API_KEY")
        self._base_url = base_url
        self._client_kwargs = client_kwargs
        self._client: Any = None  # lazy — keeps __init__ cheap and offline-friendly

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import OpenAI  # type: ignore[import-not-found]

            init_kwargs: dict[str, Any] = {"api_key": self._api_key}
            if self._base_url is not None:
                init_kwargs["base_url"] = self._base_url
            init_kwargs.update(self._client_kwargs)
            self._client = OpenAI(**init_kwargs)
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

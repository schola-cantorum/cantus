"""Google Gemini adapter for Tier 2 ChatModel.

Uses the **new** unified Gemini API SDK — `google-genai` on PyPI, import
path ``from google import genai``. The legacy `google-generativeai` package
is intentionally NOT supported: its `GenerativeModel(...).generate_content`
shape differs from `client.models.generate_content`, and the new SDK is the
forward-compatible path to Vertex AI in v0.3+.

System prompts are passed via the top-level `system_instruction` kwarg
of `generate_content`, not inside `contents` — `to_google_messages()`
extracts them. Tool use is content-block-shaped (`function_call` /
`function_response` parts); the translator hides that.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from cantus.model.chat import ChatResponse, Message
from cantus.model.providers._common import resolve_api_key
from cantus.model.providers._translate import (
    from_google_response,
    to_google_messages,
)


class GoogleChatModel:
    """Tier 2 adapter for the google-genai Gemini API."""

    supports_tool_use = True

    def __init__(
        self,
        model_id: str,
        api_key: str | None = None,
        **client_kwargs: Any,
    ) -> None:
        self.model_id = model_id
        self._api_key = resolve_api_key(api_key, "GOOGLE_API_KEY")
        self._client_kwargs = client_kwargs
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            from google import genai  # type: ignore[import-not-found]

            self._client = genai.Client(api_key=self._api_key, **self._client_kwargs)
        return self._client

    def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        client = self._get_client()
        system, contents = to_google_messages(messages)
        request_kwargs: dict[str, Any] = {
            "model": self.model_id,
            "contents": contents,
            **kwargs,
        }
        if system is not None:
            request_kwargs["system_instruction"] = system
        if tools:
            request_kwargs["tools"] = tools
        raw = client.models.generate_content(**request_kwargs)
        return from_google_response(raw)

    def stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs: Any,
    ) -> Iterator[str]:
        client = self._get_client()
        system, contents = to_google_messages(messages)
        request_kwargs: dict[str, Any] = {
            "model": self.model_id,
            "contents": contents,
            **kwargs,
        }
        if system is not None:
            request_kwargs["system_instruction"] = system
        if tools:
            request_kwargs["tools"] = tools
        for chunk in client.models.generate_content_stream(**request_kwargs):
            text = getattr(chunk, "text", None)
            if text:
                yield text

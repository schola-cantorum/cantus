"""omlx adapter — thin subclass of OpenAIChatModel targeting a local
OpenAI-compatible MLX server (omlx / mlx-omni-server).

omlx (https://omlx.ai) and mlx-omni-server both run as a separate process on
Apple Silicon and expose an OpenAI-compatible Chat Completions wire — omlx at
``http://localhost:8000/v1`` and mlx-omni-server at
``http://localhost:10240/v1``. Because those two defaults differ and neither is
obviously "the" default, this adapter REQUIRES the caller to pass ``base_url``
explicitly; constructing without one raises ``ValueError`` naming both example
endpoints. Unlike the in-process ``MLXChatModel`` (provider prefix ``mlx``),
``OmlxChatModel`` is OpenAI-compatible and inherits ``supports_tool_use = True``
because these servers expose function calling.

These servers do not authenticate requests, so the adapter substitutes the
sentinel string ``"omlx"`` for the api_key field that the openai SDK requires;
it does NOT consult any environment variable. An explicit ``api_key=`` value is
preserved for callers who front the server with an authenticating proxy.

Because the runtime SDK is ``openai``, there is intentionally NO ``cantus[omlx]``
extras dependency closure beyond a documentary alias; install via
``pip install cantus[openai]`` (or the documentary ``pip install cantus[omlx]``
alias, which resolves to the same set).

Connection failures (server not running, wrong port) surface as the underlying
``openai.APIConnectionError`` with a long httpx stack trace that is unhelpful
to students. ``chat()`` and ``stream()`` are therefore overridden to re-raise as
``ConnectionError`` with an actionable message naming the server URL. All other
openai exception types propagate unchanged so callers can distinguish "server
down" from "model not loaded" (``openai.NotFoundError``).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import openai

from cantus.model.chat import ChatResponse, Message
from cantus.model.providers.openai import OpenAIChatModel


OMLX_API_KEY_SENTINEL = "omlx"
OMLX_EXAMPLE_URL = "http://localhost:8000/v1"
MLX_OMNI_EXAMPLE_URL = "http://localhost:10240/v1"


class OmlxChatModel(OpenAIChatModel):
    """Tier 2 adapter for a local OpenAI-compatible MLX server (omlx / mlx-omni-server).

    base_url is required — pass the server's /v1 endpoint
    (http://localhost:8000/v1 for omlx, http://localhost:10240/v1 for
    mlx-omni-server). The api_key parameter is accepted but is not authoritative
    on the local server side: these servers do not authenticate requests, so the
    adapter substitutes the sentinel "omlx" when no key is given (None or an
    empty string both count as "no key"). Pass a non-empty explicit api_key=
    only if you front the server with an authenticating proxy.
    """

    def __init__(
        self,
        model_id: str,
        api_key: str | None = None,
        base_url: str | None = None,
        **client_kwargs: Any,
    ) -> None:
        if base_url is None:
            raise ValueError(
                "OmlxChatModel requires an explicit base_url naming the local "
                "OpenAI-compatible MLX server, e.g. "
                f'base_url="{OMLX_EXAMPLE_URL}" (omlx) or '
                f'base_url="{MLX_OMNI_EXAMPLE_URL}" (mlx-omni-server).'
            )
        # Coalesce on truthiness, not `is not None`: an empty/blank api_key is
        # treated as absent so the sentinel is used. Using `is not None` would
        # forward `""` to the parent, whose resolve_api_key falls back to
        # OPENAI_API_KEY — silently re-opening the env consultation this adapter
        # is meant to avoid (spectra-audit hardening).
        resolved_key = api_key if api_key else OMLX_API_KEY_SENTINEL
        super().__init__(
            model_id=model_id,
            api_key=resolved_key,
            base_url=base_url,
            **client_kwargs,
        )

    def _connection_error_message(self) -> str:
        return (
            f"Cannot reach the local MLX server at {self._base_url}. "
            f"Is `omlx` or `mlx-omni-server` running? "
            f"Start the server, then retry."
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

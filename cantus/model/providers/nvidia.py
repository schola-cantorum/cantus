"""NVIDIA NIM adapter — thin subclass of OpenAIChatModel.

NVIDIA NIM exposes an OpenAI-compatible Chat Completions wire at
``https://integrate.api.nvidia.com/v1``, so the adapter is just an
`OpenAIChatModel` subclass that (1) defaults `base_url` to the NIM endpoint
and (2) reads `NVIDIA_API_KEY` instead of `OPENAI_API_KEY`. All chat /
stream / translator behavior is inherited unchanged. Because the runtime
SDK is `openai`, there is intentionally NO `cantus[nvidia]` extras group;
install via `pip install cantus[openai]`.
"""

from __future__ import annotations

from typing import Any

from cantus.model.providers._common import resolve_api_key
from cantus.model.providers.openai import OpenAIChatModel


NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


class NvidiaChatModel(OpenAIChatModel):
    """Tier 2 adapter for NVIDIA NIM (OpenAI-compatible)."""

    def __init__(
        self,
        model_id: str,
        api_key: str | None = None,
        base_url: str | None = None,
        **client_kwargs: Any,
    ) -> None:
        resolved_key = resolve_api_key(api_key, "NVIDIA_API_KEY")
        super().__init__(
            model_id=model_id,
            api_key=resolved_key,
            base_url=base_url if base_url is not None else NIM_BASE_URL,
            **client_kwargs,
        )

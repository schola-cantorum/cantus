"""`load_chat_model` — factory that dispatches a provider spec to an adapter.

The factory parses `"<provider>/<model_id>"` and lazy-imports the matching
adapter module so users who only need one provider don't pay the import
cost of the others (and so missing optional extras surface as actionable
`ImportError` messages instead of import-time crashes).

cantus ships seven providers — `openai`, `anthropic`, `google`, `groq`,
`nvidia`, `ollama`, and `mlx`. NVIDIA NIM and the local Ollama daemon are both
OpenAI-compatible at the wire layer (subclasses of `OpenAIChatModel`), so
their missing-extras hints point at `cantus[openai]` rather than phantom
`cantus[nvidia]` / `cantus[ollama]` packages. The `mlx` adapter runs mlx-lm
in-process on Apple Silicon and has its own `cantus[mlx]` extras closure.
"""

from __future__ import annotations

import importlib
from typing import Any

from cantus.model.chat import ChatModel


_REGISTRY: dict[str, tuple[str, str]] = {
    "openai": ("cantus.model.providers.openai", "OpenAIChatModel"),
    "anthropic": ("cantus.model.providers.anthropic", "AnthropicChatModel"),
    "google": ("cantus.model.providers.google", "GoogleChatModel"),
    "groq": ("cantus.model.providers.groq", "GroqChatModel"),
    "nvidia": ("cantus.model.providers.nvidia", "NvidiaChatModel"),
    "ollama": ("cantus.model.providers.ollama", "OllamaChatModel"),
    "mlx": ("cantus.model.providers.mlx", "MLXChatModel"),
}

# NVIDIA's adapter runs on the openai SDK (NIM exposes an OpenAI-compatible
# endpoint), so its missing-extras hint must point at the openai extras group
# rather than a non-existent `cantus[nvidia]`. Ollama follows the same pattern
# (the local daemon exposes an OpenAI-compatible endpoint). Keeping the map
# explicit makes the special cases auditable. The `mlx` adapter is in-process
# (mlx-lm on Apple Silicon), not OpenAI-compatible, so it carries its own
# `cantus[mlx]` extras closure rather than aliasing `openai`.
_EXTRAS_HINT: dict[str, str] = {
    "openai": "openai",
    "anthropic": "anthropic",
    "google": "google",
    "groq": "groq",
    "nvidia": "openai",
    "ollama": "openai",
    "mlx": "mlx",
}


def load_chat_model(spec: str, **kwargs: Any) -> ChatModel:
    """Construct a `ChatModel` from a provider/model_id spec string.

    Args:
        spec: ``"<provider>/<model_id>"``, e.g. ``"anthropic/claude-sonnet-4-6"``.
            Supported providers: {supported_providers}.
        **kwargs: forwarded to the adapter constructor (``api_key``,
            ``base_url``, etc.).

    Raises:
        ValueError: if `spec` is malformed or the provider prefix is
            unsupported.
        ImportError: if the adapter module's optional dependency is not
            installed; the message contains the exact installation hint
            ``pip install cantus[<extras-group>]``.
    """
    provider, model_id = _parse_spec(spec)

    if provider not in _REGISTRY:
        supported = ", ".join(sorted(_REGISTRY))
        raise ValueError(
            f"unsupported provider {provider!r}; supported providers: {supported}"
        )

    module_path, class_name = _REGISTRY[provider]
    extras_group = _EXTRAS_HINT[provider]
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ImportError(
            f"adapter for provider {provider!r} requires its optional extras. "
            f"Run: pip install cantus[{extras_group}]"
        ) from exc

    adapter_cls = getattr(module, class_name)
    instance: ChatModel = adapter_cls(model_id=model_id, **kwargs)
    return instance


assert load_chat_model.__doc__ is not None
load_chat_model.__doc__ = load_chat_model.__doc__.format(
    supported_providers=", ".join(sorted(_REGISTRY))
)


def _parse_spec(spec: str) -> tuple[str, str]:
    if "/" not in spec:
        raise ValueError(
            f"spec {spec!r} must be of the form 'provider/model_id' "
            f"(e.g. 'openai/gpt-4o-mini')"
        )
    provider, model_id = spec.split("/", 1)
    if not provider or not model_id:
        raise ValueError(
            f"spec {spec!r} must have a non-empty provider and model_id"
        )
    return provider, model_id

"""CloudOnlyEnvironment — refuse to load local models.

Pair with `cantus.load_chat_model("<provider>/...")` for users who only
want to reach hosted endpoints (OpenAI, Anthropic, etc.) and never want
the heavy transformers / bitsandbytes / torch import chain.

`prepare_model()` raises `RuntimeError` immediately and does NOT import
any of the local-load dependencies — verifiable via `sys.modules`.
"""

from __future__ import annotations

from typing import Any, NoReturn


class CloudOnlyEnvironment:
    """A do-nothing local environment that points callers to load_chat_model."""

    def prepare_model(self, *args: Any, **kwargs: Any) -> NoReturn:
        raise RuntimeError(
            "CloudOnlyEnvironment 不下載本地 model；"
            "請改用 cantus.load_chat_model('provider/model_id') 接 cloud provider。"
        )

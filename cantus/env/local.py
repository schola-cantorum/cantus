"""LocalEnvironment — load a model from a local path without touching Drive.

Useful when running cantus outside Colab (laptop, CI, self-hosted GPU) or
when running inside Colab but with a pre-staged model on a path other than
the Shared Drive. Never attempts `google.colab.drive.mount()`.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

from cantus.model.loader import (
    DEFAULT_DRIVE_ROOT,
    SHARED_DRIVE_ROOT_ENV,
    VARIANT_TO_DIRNAME,
    VARIANT_TO_HF_REPO,
    ModelHandle,
    ModelNotFoundError,
    _load_from_hub,
    _load_from_local,
)


class LocalEnvironment:
    """Resolve a model path without mounting Drive, then load it."""

    def prepare_model(
        self,
        variant: str,
        *,
        allow_hub_fallback: bool = False,
        drive_root: str | None = None,
    ) -> ModelHandle:
        if variant not in VARIANT_TO_HF_REPO:
            raise ValueError(
                f"Unknown variant {variant!r}. "
                f"Choose one of: {sorted(VARIANT_TO_HF_REPO)}"
            )

        root = Path(
            drive_root or os.environ.get(SHARED_DRIVE_ROOT_ENV) or DEFAULT_DRIVE_ROOT
        )
        target = root / VARIANT_TO_DIRNAME[variant]

        if target.exists():
            return _load_from_local(target, variant)

        if allow_hub_fallback:
            warnings.warn(
                f"找不到本地路徑 {target}；改從 Hugging Face Hub 下載 "
                f"{VARIANT_TO_HF_REPO[variant]}。",
                stacklevel=2,
            )
            return _load_from_hub(VARIANT_TO_HF_REPO[variant], variant)

        raise ModelNotFoundError(
            f"找不到模型權重於 {target}。請在本地預先下載 4-bit 量化版本，"
            f"或設 allow_hub_fallback=True 從 Hugging Face Hub 下載 "
            f"{VARIANT_TO_HF_REPO[variant]}。"
        )

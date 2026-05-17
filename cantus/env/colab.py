"""ColabEnvironment — mount Drive (if Colab) then load with 4-bit quantization.

Behavior must match the legacy `mount_drive_and_load()` function exactly so
v0.1.x notebooks continue to work without code changes. The shared loader
internals (path resolution + transformers init) live in
`cantus.model.loader` and are reused here.
"""

from __future__ import annotations

import os
from pathlib import Path

from cantus.model.loader import (
    DEFAULT_DRIVE_ROOT,
    SHARED_DRIVE_ROOT_ENV,
    VARIANT_TO_DIRNAME,
    VARIANT_TO_HF_REPO,
    ModelHandle,
    ModelNotFoundError,
    MountError,
    _load_from_hub,
    _load_from_local,
    _mount_colab_drive,
    _running_in_colab,
)


class ColabEnvironment:
    """Mount Drive and prepare a local Gemma 4 variant."""

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

        if _running_in_colab():
            try:
                _mount_colab_drive()
            except Exception as exc:
                raise MountError(
                    "無法掛載 Google Drive。請在 Colab 左側點選『掛載 Drive』並重試。"
                    f" Inner: {type(exc).__name__}: {exc}"
                ) from exc

        root = Path(
            drive_root or os.environ.get(SHARED_DRIVE_ROOT_ENV) or DEFAULT_DRIVE_ROOT
        )
        target = root / VARIANT_TO_DIRNAME[variant]

        if target.exists():
            return _load_from_local(target, variant)

        if allow_hub_fallback:
            import warnings

            warnings.warn(
                f"找不到 Drive 路徑 {target}；改從 Hugging Face Hub 下載 "
                f"{VARIANT_TO_HF_REPO[variant]}。",
                stacklevel=2,
            )
            return _load_from_hub(VARIANT_TO_HF_REPO[variant], variant)

        raise ModelNotFoundError(
            f"找不到模型權重於 {target}。請確認老師已將 4-bit 量化版本放在 Shared Drive，"
            f"或於呼叫時設 allow_hub_fallback=True 從 Hugging Face Hub 下載 "
            f"{VARIANT_TO_HF_REPO[variant]}。"
        )

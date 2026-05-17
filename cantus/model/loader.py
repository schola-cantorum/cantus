"""Gemma 4 loader — Drive-mount + 4-bit + optional HF Hub fallback.

The function `mount_drive_and_load(variant, allow_hub_fallback=False)`
is what students call from their Colab notebook. Outside Colab, the
function still works but skips the Drive mount step (it just looks for
the variant under `~/cantus_models/` or wherever
`CANTUS_MODEL_ROOT` points). This makes the loader testable.

Variant strings: "E4B" → google/gemma-4-E4B-it; "E2B" → google/gemma-4-E2B-it.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SHARED_DRIVE_ROOT_ENV = "CANTUS_MODEL_ROOT"
DEFAULT_DRIVE_ROOT = "/content/drive/Shareddrives/colab-llm-agent/models"

VARIANT_TO_HF_REPO: dict[str, str] = {
    "E4B": "google/gemma-4-E4B-it",
    "E2B": "google/gemma-4-E2B-it",
}

VARIANT_TO_DIRNAME: dict[str, str] = {
    "E4B": "gemma-4-E4B-it-4bit",
    "E2B": "gemma-4-E2B-it-4bit",
}


class MountError(RuntimeError):
    """Raised when Google Drive cannot be mounted."""


class ModelNotFoundError(FileNotFoundError):
    """Raised when the variant directory is missing on Drive and fallback is off."""


@dataclass
class ModelHandle:
    """What the loader returns. The agent uses `.generate(prompt)`."""

    model: Any
    tokenizer: Any
    processor: Any | None
    variant: str

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Convenience wrapper around `model.generate`."""
        if self.tokenizer is None or self.model is None:
            raise RuntimeError("ModelHandle has no model; was it stub-loaded?")
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        out = self.model.generate(**inputs, max_new_tokens=kwargs.get("max_new_tokens", 256))
        return self.tokenizer.decode(out[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True)


def mount_drive_and_load(
    variant: str,
    allow_hub_fallback: bool = False,
    drive_root: str | None = None,
) -> ModelHandle:
    """Mount Drive (if running under Colab) and load the named variant.

    Thin backward-compatible wrapper around `ColabEnvironment().prepare_model(...)` —
    the signature, exception types, and observable behavior match v0.1.x exactly,
    and no DeprecationWarning is emitted in v0.2.0.

    Parameters:
        variant: "E4B" or "E2B".
        allow_hub_fallback: when True, fall back to HF Hub download if
            the Drive path is missing. Default False so misconfigured
            Drive setups surface loudly.
        drive_root: override the directory we look in. Defaults to
            $CANTUS_MODEL_ROOT or the on-Drive shared path.

    Returns:
        ModelHandle with `.model`, `.tokenizer`, `.processor`, `.variant`.

    Raises:
        ValueError: unknown variant.
        MountError: Drive mount failed in a Colab session.
        ModelNotFoundError: variant dir absent and fallback disabled.
    """
    from cantus.env.colab import ColabEnvironment

    return ColabEnvironment().prepare_model(
        variant,
        allow_hub_fallback=allow_hub_fallback,
        drive_root=drive_root,
    )


def _running_in_colab() -> bool:
    return "google.colab" in sys.modules


def _mount_colab_drive() -> None:  # pragma: no cover — Colab-only path
    from google.colab import drive  # type: ignore

    drive.mount("/content/drive", force_remount=False)


def _load_from_local(target: Path, variant: str) -> ModelHandle:
    """Load model + tokenizer from a local directory with 4-bit config."""
    return _load_with_quant_config(str(target), variant)


def _load_from_hub(repo_id: str, variant: str) -> ModelHandle:
    """Download from HF Hub and load with 4-bit config."""
    return _load_with_quant_config(repo_id, variant)


def _load_with_quant_config(model_id_or_path: str, variant: str) -> ModelHandle:
    try:
        import torch  # type: ignore
        from transformers import (  # type: ignore
            AutoModelForCausalLM,
            AutoProcessor,
            AutoTokenizer,
            BitsAndBytesConfig,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Loader requires the `runtime` extras. "
            "Install with: pip install 'cantus[runtime]'"
        ) from exc

    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(model_id_or_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_id_or_path,
        quantization_config=quant,
        device_map="auto",
    )
    try:
        processor = AutoProcessor.from_pretrained(model_id_or_path)
    except Exception:
        processor = None
    return ModelHandle(
        model=model, tokenizer=tokenizer, processor=processor, variant=variant
    )

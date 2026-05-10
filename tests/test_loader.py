"""Loader: variant validation, missing path errors, fallback opt-in."""

import os
from pathlib import Path

import pytest

from cantus.model.loader import (
    ModelNotFoundError,
    VARIANT_TO_DIRNAME,
    VARIANT_TO_HF_REPO,
    mount_drive_and_load,
)


def test_unknown_variant_raises():
    with pytest.raises(ValueError):
        mount_drive_and_load("E8B")


def test_missing_drive_path_raises_when_fallback_off(tmp_path: Path):
    with pytest.raises(ModelNotFoundError):
        mount_drive_and_load("E4B", drive_root=str(tmp_path), allow_hub_fallback=False)


def test_variant_dirname_mapping_complete():
    for v in VARIANT_TO_HF_REPO:
        assert v in VARIANT_TO_DIRNAME


def test_e4b_e2b_in_mapping():
    assert "E4B" in VARIANT_TO_HF_REPO
    assert "E2B" in VARIANT_TO_HF_REPO
    assert VARIANT_TO_HF_REPO["E4B"] == "google/gemma-4-E4B-it"
    assert VARIANT_TO_HF_REPO["E2B"] == "google/gemma-4-E2B-it"


def test_drive_root_env_override(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CANTUS_MODEL_ROOT", str(tmp_path))
    # Path doesn't exist under tmp_path; should still raise ModelNotFoundError
    # (not a different error) because the override worked.
    with pytest.raises(ModelNotFoundError):
        mount_drive_and_load("E4B", allow_hub_fallback=False)

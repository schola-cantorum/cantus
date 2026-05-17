"""Tests for the three Environment profiles."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from cantus.env import CloudOnlyEnvironment, ColabEnvironment, LocalEnvironment
from cantus.model.loader import ModelNotFoundError, MountError


# ---------- ColabEnvironment ------------------------------------------------


def test_colab_environment_unknown_variant_raises_value_error():
    with pytest.raises(ValueError):
        ColabEnvironment().prepare_model("E8B")


def test_colab_environment_missing_path_raises_model_not_found(tmp_path: Path):
    """When not in Colab and fallback off, behaves identically to mount_drive_and_load."""
    with pytest.raises(ModelNotFoundError):
        ColabEnvironment().prepare_model(
            "E4B", drive_root=str(tmp_path), allow_hub_fallback=False
        )


def test_colab_environment_attempts_drive_mount_when_in_colab(tmp_path: Path):
    """When _running_in_colab() returns True, _mount_colab_drive must be invoked."""
    with patch("cantus.env.colab._running_in_colab", return_value=True), patch(
        "cantus.env.colab._mount_colab_drive"
    ) as mock_mount:
        with pytest.raises(ModelNotFoundError):
            ColabEnvironment().prepare_model(
                "E4B", drive_root=str(tmp_path), allow_hub_fallback=False
            )
        mock_mount.assert_called_once()


def test_colab_environment_mount_failure_wraps_as_mount_error(tmp_path: Path):
    with patch("cantus.env.colab._running_in_colab", return_value=True), patch(
        "cantus.env.colab._mount_colab_drive",
        side_effect=RuntimeError("permission denied"),
    ):
        with pytest.raises(MountError) as exc:
            ColabEnvironment().prepare_model("E4B", drive_root=str(tmp_path))
        assert "Google Drive" in str(exc.value)


def test_colab_environment_observable_behavior_matches_mount_drive_and_load(tmp_path: Path):
    """Cross-check: both raise the same exception type for the same input."""
    from cantus.model.loader import mount_drive_and_load

    with patch("cantus.env.colab._running_in_colab", return_value=False):
        with pytest.raises(ModelNotFoundError) as env_exc:
            ColabEnvironment().prepare_model("E4B", drive_root=str(tmp_path))

    with patch("cantus.model.loader._running_in_colab", return_value=False):
        with pytest.raises(ModelNotFoundError) as legacy_exc:
            mount_drive_and_load("E4B", drive_root=str(tmp_path))

    # Same exception type, both reference the same expected path
    assert type(env_exc.value) is type(legacy_exc.value)
    assert "gemma-4-E4B-it-4bit" in str(env_exc.value)
    assert "gemma-4-E4B-it-4bit" in str(legacy_exc.value)


# ---------- LocalEnvironment ------------------------------------------------


def test_local_environment_unknown_variant_raises_value_error():
    with pytest.raises(ValueError):
        LocalEnvironment().prepare_model("E8B")


def test_local_environment_missing_path_raises_model_not_found(tmp_path: Path):
    with pytest.raises(ModelNotFoundError):
        LocalEnvironment().prepare_model(
            "E2B", drive_root=str(tmp_path), allow_hub_fallback=False
        )


def test_local_environment_never_attempts_drive_mount_even_under_colab(tmp_path: Path):
    """Even with _running_in_colab simulated True, LocalEnvironment must NOT call mount."""
    with patch("cantus.env.colab._running_in_colab", return_value=True), patch(
        "cantus.env.colab._mount_colab_drive"
    ) as mock_mount:
        with pytest.raises(ModelNotFoundError):
            LocalEnvironment().prepare_model("E2B", drive_root=str(tmp_path))
        mock_mount.assert_not_called()


def test_local_environment_respects_cantus_model_root_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("CANTUS_MODEL_ROOT", str(tmp_path))
    with pytest.raises(ModelNotFoundError) as exc:
        LocalEnvironment().prepare_model("E4B")
    assert str(tmp_path) in str(exc.value)


# ---------- CloudOnlyEnvironment --------------------------------------------


def test_cloud_only_environment_prepare_model_raises_runtime_error():
    with pytest.raises(RuntimeError) as exc:
        CloudOnlyEnvironment().prepare_model("E4B")
    msg = str(exc.value)
    assert "load_chat_model" in msg
    assert "cloud provider" in msg or "Cloud" in msg or "provider" in msg


def test_cloud_only_environment_accepts_any_args():
    """Must not raise TypeError on extra args — fail with the same RuntimeError."""
    with pytest.raises(RuntimeError):
        CloudOnlyEnvironment().prepare_model("anything", with_arbitrary=True, kwargs="yes")


def test_cloud_only_environment_does_not_import_heavy_local_load_deps():
    """Importing CloudOnlyEnvironment alone must not drag in transformers/torch/bitsandbytes."""
    # Snapshot before
    before = set(sys.modules)
    # Force a re-import path: import the module fresh
    import importlib

    import cantus.env.cloud_only as cmod

    importlib.reload(cmod)
    # Calling prepare_model must not import the heavy deps either
    with pytest.raises(RuntimeError):
        cmod.CloudOnlyEnvironment().prepare_model("anything")
    after = set(sys.modules)
    new_modules = after - before
    forbidden = {"transformers", "bitsandbytes", "torch"}
    leaked = new_modules & forbidden
    assert not leaked, f"CloudOnlyEnvironment imported heavy deps: {leaked}"

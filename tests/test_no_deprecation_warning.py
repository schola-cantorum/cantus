"""mount_drive_and_load must not emit DeprecationWarning in v0.2.0.

The v0.2.0 release explicitly preserves the v0.1.x public surface as a
thin wrapper around ColabEnvironment. v0.1.x notebooks SHALL keep working
without code changes AND without warnings cluttering the Colab output.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from cantus.model.loader import ModelNotFoundError, mount_drive_and_load


def test_mount_drive_and_load_does_not_emit_deprecation_warning(tmp_path: Path):
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        with pytest.raises(ModelNotFoundError):
            mount_drive_and_load(
                "E4B", drive_root=str(tmp_path), allow_hub_fallback=False
            )
    dep_warnings = [w for w in captured if issubclass(w.category, DeprecationWarning)]
    assert dep_warnings == [], (
        "mount_drive_and_load must not emit DeprecationWarning in v0.2.0: "
        f"got {[str(w.message) for w in dep_warnings]}"
    )


def test_mount_drive_and_load_preserves_value_error_for_unknown_variant():
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        with pytest.raises(ValueError):
            mount_drive_and_load("E8B")
    assert all(
        not issubclass(w.category, DeprecationWarning) for w in captured
    )

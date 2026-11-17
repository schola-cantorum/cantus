"""Fixtures for the legacy-name tests."""

from __future__ import annotations

import pytest

from cantus.core.registry import _get_global_registry


@pytest.fixture(autouse=True)
def _clean_global_registry():
    """Empty the global registry before and after each legacy test."""
    _get_global_registry().clear()
    yield
    _get_global_registry().clear()

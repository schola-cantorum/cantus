"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from cantus.core.registry import _get_global_registry


@pytest.fixture(autouse=True)
def _isolate_registry():
    """Each test gets a clean global registry."""
    reg = _get_global_registry()
    saved = {k: dict(v) for k, v in reg._by_kind.items()}
    reg.clear()
    yield
    reg.clear()
    reg._by_kind.update(saved)

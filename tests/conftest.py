"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from cantus.core.registry import get_registry


@pytest.fixture(autouse=True)
def _isolate_registry():
    """Each test gets a clean global registry."""
    reg = get_registry()
    saved = {k: dict(v) for k, v in reg._by_kind.items()}
    reg.clear()
    yield
    reg.clear()
    reg._by_kind.update(saved)

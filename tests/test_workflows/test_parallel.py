"""Parallel: fan input to every branch, gather outputs in declaration order."""

from __future__ import annotations

import pytest

from cantus.core.registry import get_registry
from cantus.protocols.skill import skill
from cantus.workflows import Parallel


def test_parallel_runs_every_branch_with_same_input():
    calls: list[str] = []

    @skill
    def en(text: str) -> str:
        """EN."""
        calls.append(f"en:{text}")
        return f"en-{text}"

    @skill
    def zh(text: str) -> str:
        """ZH."""
        calls.append(f"zh:{text}")
        return f"zh-{text}"

    fanout = Parallel(branches=[en, zh])
    out = fanout.run("hello")

    assert out == ["en-hello", "zh-hello"]
    # both branches were called with the same input
    assert calls == ["en:hello", "zh:hello"]


def test_parallel_preserves_branch_order():
    @skill
    def a(x: str) -> str:
        """A."""
        return "A"

    @skill
    def b(x: str) -> str:
        """B."""
        return "B"

    @skill
    def c(x: str) -> str:
        """C."""
        return "C"

    out = Parallel(branches=[a, b, c]).run("ignored")
    assert out == ["A", "B", "C"]


def test_parallel_does_not_pollute_registry():
    @skill
    def b(x: str) -> str:
        """B."""
        return x

    Parallel(branches=[b]).run("x")
    assert "Parallel" not in get_registry().names_for("skill")
    assert "fanout" not in get_registry().names_for("skill")


def test_parallel_empty_branches_raises():
    with pytest.raises(ValueError):
        Parallel(branches=[])

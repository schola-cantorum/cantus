"""PromptChain: sequential composition; output threading; no registry mutation."""

from __future__ import annotations

import pytest

from cantus import tool
from cantus.core.registry import _get_global_registry
from cantus.workflows import PromptChain


def test_prompt_chain_runs_steps_in_order_threading_output():
    calls: list[tuple[str, str]] = []

    @tool
    def outline(topic: str) -> str:
        """Outline."""
        calls.append(("outline", topic))
        return f"outline:{topic}"

    @tool
    def draft(seed: str) -> str:
        """Draft."""
        calls.append(("draft", seed))
        return f"draft:{seed}"

    @tool
    def polish(seed: str) -> str:
        """Polish."""
        calls.append(("polish", seed))
        return f"polish:{seed}"

    chain = PromptChain(steps=[outline, draft, polish])
    result = chain.run("haiku about Tainan")

    assert result == "polish:draft:outline:haiku about Tainan"
    assert [c[0] for c in calls] == ["outline", "draft", "polish"]
    assert calls[1][1] == "outline:haiku about Tainan"
    assert calls[2][1] == "draft:outline:haiku about Tainan"


def test_prompt_chain_does_not_pollute_registry():
    @tool
    def step(x: str) -> str:
        """No-op."""
        return x

    chain = PromptChain(steps=[step])
    chain.run("x")

    assert _get_global_registry().names_for("tool") == []


def test_prompt_chain_empty_steps_raises():
    with pytest.raises(ValueError):
        PromptChain(steps=[])

"""PromptChain: sequential composition; output threading; no registry mutation."""

from __future__ import annotations

import pytest

from cantus.core.registry import get_registry
from cantus.protocols.skill import skill
from cantus.workflows import PromptChain


def test_prompt_chain_runs_steps_in_order_threading_output():
    calls: list[tuple[str, str]] = []

    @skill
    def outline(topic: str) -> str:
        """Outline."""
        calls.append(("outline", topic))
        return f"outline:{topic}"

    @skill
    def draft(seed: str) -> str:
        """Draft."""
        calls.append(("draft", seed))
        return f"draft:{seed}"

    @skill
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
    @skill
    def step(x: str) -> str:
        """No-op."""
        return x

    chain = PromptChain(steps=[step])
    chain.run("x")

    assert "PromptChain" not in get_registry().names_for("skill")
    assert "chain" not in get_registry().names_for("skill")


def test_prompt_chain_empty_steps_raises():
    with pytest.raises(ValueError):
        PromptChain(steps=[])

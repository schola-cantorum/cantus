"""EvaluatorOptimizer: generator/evaluator loop; max_iters cap; Result-aware."""

from __future__ import annotations

import pytest

from cantus.core.registry import get_registry
from cantus.core.result import Result
from cantus.protocols.skill import skill
from cantus.workflows import EvaluatorOptimizer


def test_evaluator_optimizer_second_iter_approved():
    """Second generator output passes the evaluator; result.value is returned."""
    counter = {"n": 0}

    @skill
    def generate(topic: str) -> str:
        """Generate a candidate."""
        counter["n"] += 1
        return f"draft-{counter['n']}:{topic}"

    @skill
    def evaluate(candidate: str) -> Result:
        """Accept on the second try."""
        if counter["n"] >= 2:
            return Result.success(candidate + "-approved")
        return Result.failure("not good enough")

    eo = EvaluatorOptimizer(generator=generate, evaluator=evaluate, max_iters=3)
    out = eo.run("solar power")

    assert counter["n"] == 2
    assert out == "draft-2:solar power-approved"


def test_evaluator_optimizer_max_iters_exhausted_returns_last_candidate():
    """When the evaluator never approves, the last candidate SHALL still be returned."""

    @skill
    def generate(input: str) -> str:
        """Generate."""
        return f"draft:{input}"

    @skill
    def evaluate(candidate: str) -> Result:
        """Always rejects."""
        return Result.failure("never satisfied")

    eo = EvaluatorOptimizer(generator=generate, evaluator=evaluate, max_iters=2)
    out = eo.run("input")
    assert out == "draft:input"


def test_evaluator_optimizer_truthy_non_result_approves():
    """A non-`Result` truthy verdict SHALL return the candidate."""
    counter = {"n": 0}

    @skill
    def generate(input: str) -> str:
        """Gen."""
        counter["n"] += 1
        return f"v{counter['n']}"

    @skill
    def evaluate(candidate: str) -> str:
        """Returns truthy on second call."""
        return "OK" if counter["n"] == 2 else ""

    eo = EvaluatorOptimizer(generator=generate, evaluator=evaluate, max_iters=4)
    assert eo.run("anything") == "v2"


def test_evaluator_optimizer_does_not_pollute_registry():
    @skill
    def g(x: str) -> str:
        """G."""
        return x

    @skill
    def e(x: str) -> Result:
        """E."""
        return Result.success(x)

    EvaluatorOptimizer(generator=g, evaluator=e, max_iters=1).run("x")
    assert "EvaluatorOptimizer" not in get_registry().names_for("skill")


def test_evaluator_optimizer_max_iters_zero_rejected():
    @skill
    def g(x: str) -> str:
        """G."""
        return x

    @skill
    def e(x: str) -> Result:
        """E."""
        return Result.success(x)

    with pytest.raises(ValueError):
        EvaluatorOptimizer(generator=g, evaluator=e, max_iters=0)

"""Building blocks SHALL NOT mutate the registry — top-level spec stays {'skill': [...]}."""

from __future__ import annotations

from cantus.core.registry import get_registry
from cantus.protocols.skill import skill
from cantus.workflows import (
    EvaluatorOptimizer,
    OrchestratorWorker,
    Parallel,
    PromptChain,
    Router,
)


def test_spec_for_llm_top_level_only_skill_after_building_blocks_instantiated():
    """After instantiating every building block, registry.spec_for_llm() top-level
    keys SHALL contain only "skill" — none of the building block class names leak."""

    @skill
    def a(x: str) -> str:
        """A."""
        return x

    @skill
    def b(x: str) -> str:
        """B."""
        return x

    @skill
    def plan(x: str) -> list[str]:
        """Plan."""
        return [x]

    PromptChain(steps=[a, b])
    Router(routes={"a": a, "b": b}, classifier=lambda _: "a")
    Parallel(branches=[a, b])
    OrchestratorWorker(orchestrator=plan, workers=[a])
    EvaluatorOptimizer(generator=a, evaluator=b, max_iters=1)

    spec = get_registry().spec_for_llm()
    assert set(spec.keys()) == {"skill"}, (
        f"building blocks polluted spec_for_llm: {set(spec.keys())}"
    )
    skill_names = {s["name"] for s in spec["skill"]}
    for forbidden in (
        "PromptChain",
        "Router",
        "Parallel",
        "OrchestratorWorker",
        "EvaluatorOptimizer",
    ):
        assert forbidden not in skill_names, (
            f"building block {forbidden!r} leaked into skill registry"
        )

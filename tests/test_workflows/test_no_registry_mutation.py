"""Building blocks SHALL NOT mutate the registry — top-level spec stays {'tool': [...]}."""

from __future__ import annotations

from cantus import tool
from cantus.core.registry import _get_global_registry
from cantus.workflows import (
    EvaluatorOptimizer,
    OrchestratorWorker,
    Parallel,
    PromptChain,
    Router,
)


def test_spec_for_llm_top_level_only_tool_after_building_blocks_instantiated():
    """After instantiating every building block, the global registry's
    spec_for_llm() SHALL be exactly {"tool": []}: no building block registers itself."""

    @tool
    def a(x: str) -> str:
        """A."""
        return x

    @tool
    def b(x: str) -> str:
        """B."""
        return x

    @tool
    def plan(x: str) -> list[str]:
        """Plan."""
        return [x]

    PromptChain(steps=[a, b])
    Router(routes={"a": a, "b": b}, classifier=lambda _: "a")
    Parallel(branches=[a, b])
    OrchestratorWorker(orchestrator=plan, workers=[a])
    EvaluatorOptimizer(generator=a, evaluator=b, max_iters=1)

    assert _get_global_registry().spec_for_llm() == {"tool": []}
